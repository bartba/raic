# RAIC 배포 수정 히스토리

## 개요
2026-06-10 기준, RAIC intent API x86 GPU 서버 배포 과정에서 발견된 주요 문제와 적용된 수정 사항을 기록합니다.

---

## 1. TEI Embedder 모델 변경

### 문제
- `Qwen/Qwen3-Embedding-0.6B` 모델은 Sentence Transformers 포맷이 아님
- TEI 에서 `last-token` pooling 을 지정해도 실제 embedding 이 `null`로 반환됨
- 모델에 pooling 레이어가 없어 TEI 의 pooling 설정이 무의미

### 해결
- 모델: `Qwen/Qwen3-Embedding-0.6B` → `BAAI/bge-m3`
- Pooling: `last-token` → `cls`
- Dtype: `float16` 유지

### 변경 파일
- `.env.example`: `EMBEDDING_MODEL_ID=BAAI/bge-m3`, `TEI_POOLING=cls` 추가
- `docker/run_embedder.sh`: `--dtype "${TEI_DTYPE}"`, `--pooling "${TEI_POOLING}"` 인수 추가
- `docs/X86_DEPLOYMENT.md`: BGE-M3 pooling 설명 추가 (line 95)

### 검증
- BGE-M3 는 TEI 에서 완전히 지원되며 `cls` pooling正常工作
- 20 개 E2E 테스트 100% 성공

---

## 2. LLM Client 재구현 (LangChain 제거)

### 문제
- LangChain `ChatOpenAI.invoke()` 가 `timeout` 설정에도 불구하고 hanging
- 800ms timeout 으로 설정해도 830ms 에서 "Request timed out" 오류 발생
- 실제로는 LLM 이 정상 응답 중 (curl 테스트로 확인)

### 해결
- LangChain 제거, httpx 기반 직접 구현
- 명시적 timeout: `connect`, `read`, `write`, `pool` 각각 설정
- `stream: false` 명시
- 에러 타입별 명확한 메시지:
  - `httpx.TimeoutException` → "llm request timed out"
  - `httpx.RequestError` → "llm request failed: {error}"
  - HTTP 4xx/5xx → "llm request failed with status {code}"
  - Invalid JSON → "llm response is not valid JSON"
  - Missing fields → "llm response missing expected fields"

### 변경 파일
- `api/services/llm_client.py`: 완전 재구현 (LangChain 의존성 제거)
- `api/requirements.txt`: `langchain-openai==0.1.*` 제거
- `docs/X86_DEPLOYMENT.md`: "httpx 기반 OpenAI-compatible LLM client"로 수정
- `tests/unit/test_llm_client.py`: 9 개 새로운 테스트 추가 (HTTP payload, auth, timeout, error handling)

### 검증
- 모든 단위 테스트 통과 (9/9)
- LLM 응답 시간: ~1.1 초 (정상)

---

## 3. Docker 빌드 시 프록시 및 CA 인증서 처리

### 문제
- 사내 프록시 환경에서 PyPI 접속 시 SSL 인증서 오류:
  ```
  SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] ...'))
  ```
- Docker 컨테이너 내부에서 사내 CA 인증서가 인식되지 않음

### 해결
- `Dockerfile`에 프록시 build arg 추가: `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`
- CA 인증서 등록: `DigitalCity.crt` 를 `/usr/local/share/ca-certificates/`에 복사 후 `update-ca-certificates` 실행
- `pip install` 시 `--trusted-host pypi.org` 옵션 추가

### 변경 파일
- `docker/Dockerfile`: proxy build arg 추가, trusted-host 옵션
- `docker/build.sh`: `--build-arg` 로 proxy 변수 전달 추가
- `docker/Dockerfile.tei`: `DigitalCity.crt` 복사 (기존 `company-ca.crt` 에서 변경)

### 현재 상태
- `docker/Dockerfile`에는 build-time 용 `ARG HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`만 유지
- runtime proxy `ENV`는 제거되어 API 컨테이너 실행 시 프록시 설정이 이미지에 남지 않음

---

## 4. NO_PROXY 설정 추가

### 문제
- API 컨테이너 내부에서 TEI (`host.docker.internal:9091`) 와 LLM 서버에 접속할 때 사내 프록시를 우회하지 못함
- `curl localhost:9090/v1/classify`가 프록시를 통해 차단됨

### 해결
- `docker/run.sh`에서 `NO_PROXY` 환경변수 추가:
  ```bash
  -e "NO_PROXY=${NO_PROXY:-localhost,127.0.0.1,host.docker.internal}"
  ```

### 변경 파일
- `docker/run.sh`: `-e "NO_PROXY=..."` line 추가

### 검증
- NO_PROXY 설정 후 API 컨테이너 내부에서 TEI 와 LLM 정상 접속 확인

---

## 5. faiss-cpu 버전 문제

### 문제
- `api/requirements-x86.txt`에 `faiss-cpu==1.9.*`로 설정되어 있으나, 해당 버전은 **존재하지 않음**
- 실제로 존재하는 최신 버전: `faiss-cpu 1.8.0.post1`
- `numpy==1.24.*`와 `faiss-cpu 1.9.*` 간 의존성 충돌:
  - `faiss-cpu 1.9.0`은 `numpy>=1.25.0` 필요
  - 하지만 `numpy==1.24.*`로 설정되어 있어 충돌 발생

### 현재 상태
- `api/requirements-x86.txt`는 `faiss-cpu==1.8.*`로 수정됨
- `api/requirements.txt`는 `numpy==1.24.4`로 고정됨
- x86 서버에서는 `faiss-cpu 1.8.0.post1` 설치를 확인

### 변경 파일
- `api/requirements-x86.txt`: `faiss-cpu==1.9.*` → `faiss-cpu==1.8.*`
- `api/requirements.txt`: `numpy==1.24.4`

---

## 6. build_index.sh 스크립트 문제

### 문제
- `build_index.sh`가 `--mock-embeddings` 같은 추가 인수를 `build_index.py`로 전달하지 못함
- TEI 연결 실패 시 wrapper script를 통한 index 생성 우회가 불편함

### 해결
- `build_index.sh`가 `"$@"`를 전달하도록 수정
- 이제 `scripts/build_index.sh --mock-embeddings --no-faiss` 형태로 추가 옵션 전달 가능

### 변경 파일
- `scripts/build_index.sh`: `"$@"` 전달 추가
- `tests/unit/test_build_index_script.py`: shell wrapper가 추가 인수를 전달하는지 확인

---

## 7. is_valid 검증 로직 문제

### 문제
- LLM 이 필수 슬롯 (`machine_id` 등) 을 누락해도 `intent` 를 반환
- `is_valid=False`로 표시되지만, `intent="unknown"`으로 변경되지 않음
- `policy_reasons` 에만 "missing required slot" 메시지가 저장됨

### 현재 동작
```json
{
  "session_id": "test-007",
  "decision": "reject",
  "intent": "start_machine",  // unknown 이 아님
  "slots": {},
  "confidence": "high",
  "confidence_score": 0.85,
  "is_risky": true,
  "policy_reasons": ["validation_failed: missing required slot: machine_id"],
  "processing_time_ms": 1101
}
```

### 영향
- Intent 가 "unknown"이 아니므로, intent 기반 로직이 실행될 수 있음
- `is_valid` 정보가 API response 에 노출되지 않음

### 해결 방안 (미완료)
- **Option A**: `is_valid=False` 시 `intent="unknown"`으로 강제 변경
  - 장점: 명확한 거절 정책
  - 단점: 사용자가 의도한 intent 를 완전히 무시
- **Option B**: Policy 로직에서 `is_valid` 상태 고려
  - 장점: 현재 reject/confirm/execute 정책과 통합
  - 단점: 정책 로직 수정 필요
- **Option C**: LLM 프롬프트에 required slots 명시
  - 장점: 근본적인 해결
  - 단점: 프롬프트 변경 필요

---

## 8. device/component type 필드 불필요성 분석

### 발견
- `Device.type`: 현재 사용 안 함 (프롬프트에만 포함, 실제 검증 로직 없음)
- `Component.type`: `result_validator.py` 에서 타입 불일치 검증에 사용됨

### 제안
- **Device.type**: 삭제 가능
- **Component.type**: `id` 만으로 충분하므로 삭제 가능
- `target_component_type` → `target_component_id`로 변경

### 이점
- 데이터 단순화 (중복 정보 제거)
- 코드 복잡도 감소
- 일관성 향상 (`id` 하나로 모든 식별)

### 잠재적 리스크
- LLM 프롬프트 정보 손실 (하지만 `id` 가 명확하므로 영향 최소화 예상)

### 상태
- 분석 완료, 변경 전

---

## 미완료 작업

| 작업 | 상태 | 우선순위 |
|------|------|---------|
| `faiss-cpu` 버전 수정 (1.9 → 1.8) | ✅ 완료 | - |
| `is_valid` 검증 로직 개선 | ⏳ 미완료 | 🔴 높음 |
| `type` 필드 제거 | ⏳ 미완료 | 🟡 중간 |
| `build_index.sh` 스크립트 개선 | ✅ 완료 | - |

---

## 검증 결과

### E2E 테스트 (BGE-M3 사용)
- **총 테스트**: 20 개
- **성공**: 20 개 (100%)
- **실패**: 0 개
- **평균 처리 시간**: 1720ms
- **신뢰도**: 모든 테스트에서 high confidence (0.95)

### 테스트 커버리지
- `start_machine`: 2/2 ✅
- `stop_machine`: 2/2 ✅
- `emergency_stop`: 2/2 ✅
- `check_status`: 2/2 ✅
- `change_model`: 2/2 ✅
- `set_light_intensity`: 2/2 ✅
- `set_camera_exposure`: 2/2 ✅
- `set_camera_gain`: 2/2 ✅
- `set_robot_speed`: 2/2 ✅
- `check_plc_status`: 2/2 ✅

---

## 참고 자료

- `docs/X86_DEPLOYMENT.md`: x86 GPU 서버 배포 절차
- `tests/test_e2e_classification.py`: E2E 테스트 스크립트
- `tests/unit/test_llm_client.py`: LLM Client 단위 테스트
- `api/services/llm_client.py`: httpx 기반 LLM Client 구현
