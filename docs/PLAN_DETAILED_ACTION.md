# PLAN_DETAILED_ACTION.md: 단계별 코드 생성 및 테스트 세부 계획

## 1. 목적

이 문서는 `docs/PLAN_CODING.md`를 실제 코드 생성 작업으로 옮기기 위한 세부 실행 계획이다.

원칙:

- 한 단계에서 많은 파일을 만들지 않는다.
- 한 단계는 하나의 책임만 갖는다.
- 단계마다 사람이 이해할 수 있는 설명을 남긴다.
- Jetson 개발환경에서는 unit/mock 테스트를 우선한다.
- x86 GPU 서버에서는 실제 Docker, TEI, FAISS, 외부 LLM 연동을 확인한다.
- 완료된 단계는 체크박스로 표시한다.
- 불명확한 결정은 질문 게이트에서 멈추고 확인한다.

---

## 2. 환경 기준

| 구분 | 환경 | 역할 |
|---|---|---|
| 개발환경 | JETSON ORIN NX 16GB, ARM/aarch64 | 코드 작성, 문서 수정, unit/mock 테스트 |
| 실사용 테스트/양산 환경 | Ubuntu Linux 20.04 x86_64 NVIDIA GPU 서버 | Docker 실행, TEI 임베더, FAISS, 외부 LLM, E2E/성능 테스트 |

Jetson에서 통과한 테스트는 코드 로직 검증으로만 본다. 실사용 가능 여부는 x86 GPU 서버에서 확인한다.

---

## 3. 진행 현황

- [x] 0. 구현 전 결정사항 확인
- [x] 1. 프로젝트 스캐폴딩
- [x] 2. 설정과 기본 모델
- [x] 3. 데이터 스키마와 샘플 데이터
- [x] 4. 스키마 로더
- [x] 5. 정규화 모듈
- [x] 6. 정책 엔진
- [x] 7. LLM 결과 검증
- [x] 8. Prompt 빌더
- [x] 9. 외부 클라이언트
- [x] 10. FAISS VectorStore
- [x] 11. 파이프라인 조립
- [x] 12. FastAPI 라우터
- [x] 13. 인증, 로깅, 메트릭
- [x] 14. Docker와 실행 스크립트
- [x] 15. Jetson 통합 점검
- [x] 16. x86 GPU 서버 수동 테스트 절차 이관
- [x] 17. 피드백 반영 절차 이관

---

## 4. 질문 게이트

구현 중 아래 지점에서는 질문을 하고 답을 받은 뒤 진행한다.

| 게이트 | 질문 주제 | 필요한 이유 |
|---|---|---|
| QG-1 | Python 패키지 구조와 실행 방식 | import 경로와 테스트 구조를 초기에 고정하기 위해 |
| QG-2 | 샘플 intent/device 범위 | 테스트 데이터가 너무 크거나 작아지는 것을 막기 위해 |
| QG-3 | API 인증 방식 | static token 방식으로 충분한지 확인하기 위해 |
| QG-4 | 외부 LLM 응답 형식 | mock과 실제 서버 응답 차이를 줄이기 위해 |
| QG-5 | x86 서버 수동 복사 방식 | 실사용 테스트 반복 절차를 명확히 하기 위해 |

---

## 5. 단계별 실행 계획

### 0. 구현 전 결정사항 확인

- [x] 0.1 현재 문서 기준 재확인
  - 작업: `README.md`, `docs/PRD.md`, `docs/PLAN_CODING.md`를 읽고 구현 범위를 확인한다.
  - 산출물: 없음
  - Jetson 테스트: 없음
  - 설명: 코드 생성 전 범위가 바뀌지 않았는지 확인한다.

- [x] 0.2 QG-1 질문
  - 결정: `api/`를 코드 루트로 사용하는 방식 A로 진행한다.
  - 실행 기준: 테스트는 `PYTHONPATH=.:api pytest` 방식으로 실행한다.
  - 설명: import 경로를 짧고 단순하게 유지한다. 예: `from services.policy_engine import decide`

- [x] 0.3 QG-2 질문
  - 결정: 초기 샘플 intent는 장비 제어, 모델 변경, 조명/카메라/로봇 파라미터 변경과 PLC 제품 동작 명령으로 확장한다.
  - 설명: 장비는 equipment 단위로 등록하고, 카메라/조명/로봇/PLC는 하위 component로 관리한다.

완료 기준:

- [x] 구현 범위와 첫 샘플 데이터 범위가 확정된다.

---

### 1. 프로젝트 스캐폴딩

- [x] 1.1 디렉터리 생성
  - 생성: `api/`, `api/routers/`, `api/services/`, `api/models/`, `api/middleware/`, `data/`, `data/golden/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/scenarios/`, `scripts/`, `docker/`
  - Jetson 테스트: `find` 또는 `rg --files`로 구조 확인
  - 설명: 빈 골격만 만든다. 아직 비즈니스 로직은 넣지 않는다.

- [x] 1.2 최소 의존성 파일 생성
  - 생성: `api/requirements.txt`, `api/requirements-x86.txt`
  - Jetson 기본 포함: FastAPI, uvicorn, pydantic-settings, httpx, pyyaml, `numpy==1.24.4`, prometheus-client, structlog, pytest
  - x86 서버 추가 포함: `faiss-cpu==1.8.*`
  - Jetson 테스트: `.venv` 생성 후 기본 의존성 설치와 `pip check` 확인
  - 설명: Jetson 개발환경에서는 ARM/aarch64 호환성이 높은 기본 의존성만 설치하고, 실제 FAISS는 x86 서버에서 확인한다.

- [x] 1.3 최소 앱 진입점 생성
  - 생성: `api/main.py`
  - 내용: FastAPI 앱 객체와 health 라우터 연결만 포함
  - Jetson 테스트: Python import 가능 여부와 `/health` 라우터 연결 확인
  - 설명: 서버 기능보다 import 가능한 구조를 먼저 만든다.
  - 완료: `api/main.py`와 `api/routers/health.py`를 생성했고, 문법 검증, 앱 import, `/health` 함수 응답, 라우터 등록을 확인했다.

완료 기준:

- [x] 기본 디렉터리와 최소 앱 파일이 존재한다.
- [x] 아직 외부 서비스 호출 코드는 없다.

---

### 2. 설정과 기본 모델

- [x] 2.1 설정 모델 작성
  - 생성: `api/config.py`
  - 내용: `Settings` 클래스, 기본값, 필수 환경 변수
  - Jetson 테스트: 환경 변수를 mock해 설정 로드 테스트
  - 설명: 외부 URL과 토큰은 코드에 하드코딩하지 않는다.
  - 완료: `LLM_API_URL`, `API_AUTH_TOKEN` 필수 검증과 기본값 로드를 확인했다.

- [x] 2.2 request/response 모델 작성
  - 생성: `api/models/common.py`, `api/models/request.py`, `api/models/response.py`
  - 내용: `ClassifyRequest`, `ClassifyResponse`
  - Jetson 테스트: Pydantic validation 테스트
  - 설명: API 입출력 형태를 먼저 고정한다.
  - 완료: 요청의 빈 발화 거부와 PRD 응답 형태를 확인했고, 공용 타입을 `common.py`로 분리했다.

- [x] 2.3 내부 스키마 모델 작성
  - 생성: `api/models/schema.py`
  - 내용: `IntentDef`, `SlotDef`, `DeviceDef`, `Candidate`, `ValidatedResult`, `PolicyDecision`
  - Jetson 테스트: 모델 생성 테스트
  - 설명: dict를 계속 넘기지 않고, 읽기 쉬운 타입으로 흐름을 만든다.
  - 완료: intent, slot, device, candidate, validation, policy decision 모델 생성을 확인했다.

완료 기준:

- [x] 요청/응답/내부 모델이 독립적으로 생성되고 검증된다.

---

### 3. 데이터 스키마와 샘플 데이터

- [x] 3.1 intent 샘플 작성
  - 생성: `data/intents.yaml`
  - 내용: equipment/component intent, slot, risk, required capability, seed utterances
  - Jetson 테스트: YAML 파싱 확인
  - 설명: intent는 특정 장비 ID 대신 `required_capability`와 `target_scope`를 기준으로 정의한다.
  - 완료: 장비 공통 명령, 비상정지 명령, 조명/카메라/로봇 component 명령, PLC 제품 동작 명령을 포함해 18개 intent를 작성했다.

- [x] 3.2 device 샘플 작성
  - 생성: `data/devices.yaml`
  - 내용: equipment, component, alias, capability
  - Jetson 테스트: YAML 파싱 확인
  - 설명: 장비는 최상위 equipment로 등록하고, `camera`, `led_light`, `robot`, `plc`는 하위 component로 둔다.
  - 완료: `machine_inspection` 장비와 하위 `camera`, `led_light`, `robot`, `plc` 컴포넌트 및 capability를 작성했다.

- [x] 3.3 골든셋 초안 작성
  - 생성: `data/golden/phase1_golden.yaml`
  - 내용: intent별 대표 발화, PLC 제품 동작 발화, OOD 2개
  - Jetson 테스트: YAML 파싱 확인
  - 설명: 실제 품질 평가는 나중에 확장한다.
  - 완료: 현재 17개 intent에 대응하는 대표 발화와 OOD 2개를 포함한 phase1 골든셋을 작성했다.

완료 기준:

- [x] 세 YAML 파일이 모두 파싱된다.
- [x] 데이터는 작고 사람이 눈으로 검토 가능하다.

---

### 4. 스키마 로더

- [x] 4.1 `schema_manager.py` 기본 로더 작성
  - 생성: `api/services/schema_manager.py`
  - 내용: intent/device YAML 로드
  - Jetson 테스트: 정상 YAML 로드 테스트
  - 설명: 파일 읽기와 모델 변환만 담당한다.
  - 완료: `load_schema()` 진입점으로 `data/intents.yaml`, `data/devices.yaml`을 `IntentDef`, `DeviceDef` 모델로 로드한다.

- [x] 4.2 스키마 자체 검증 추가
  - 수정: `schema_manager.py`
  - 검증: 중복 intent, 중복 device id, component id, 필수 필드 누락, 잘못된 slot type, capability 참조
  - Jetson 테스트: 정상/오류 fixture 테스트
  - 설명: 런타임 전에 잘못된 설정을 빨리 발견한다.
  - 완료: 중복 intent/device/component, 잘못된 slot type, enum values 누락, unknown capability를 명확한 `SchemaError`로 처리한다.

- [x] 4.3 조회 API 추가
  - 수정: `schema_manager.py`
  - 내용: `get_intent`, `is_valid_intent`, `get_device`, `list_seed_examples`
  - Jetson 테스트: 조회 단위 테스트
  - 설명: 다른 모듈이 YAML 구조를 직접 알 필요 없게 한다.
  - 완료: intent/device 조회와 seed utterance 목록 조회를 테스트했고, helper 함수 수를 줄여 흐름을 단순화했다.

완료 기준:

- [x] 정상 데이터는 로드된다.
- [x] 잘못된 데이터는 명확한 오류로 실패한다.

---

### 5. 정규화 모듈

- [x] 5.1 기본 텍스트 정규화 작성
  - 생성: `api/services/normalizer.py`
  - 내용: 공백 정리, 대소문자, 단위 표기 간단 정규화
  - Jetson 테스트: 입력/출력 문자열 테스트
  - 설명: 복잡한 NLP보다 명시적 규칙만 둔다.
  - 완료: 공백 압축, 영문 소문자화, 단위 문자열과 간단한 번호 표현 치환을 구현했다.

- [x] 5.2 장비 alias 매칭 작성
  - 수정: `normalizer.py`
  - 내용: `devices.yaml`의 equipment/component alias 기반 후보 반환
  - Jetson 테스트: 장비 alias, 카메라/조명 component alias 매핑 확인
  - 설명: 장비명 해석은 LLM에만 맡기지 않는다.
  - 완료: `find_device_candidates()`, `find_device_ids()`, `find_component_ids()`로 alias 기반 후보를 반환한다.

- [x] 5.3 숫자/단위 보조 정규화 추가
  - 수정: `normalizer.py`
  - 내용: "삼번", "알피엠" 같은 최소 패턴 처리
  - Jetson 테스트: 대표 패턴만 테스트
  - 설명: 규칙이 많아지면 즉시 멈추고 데이터 보강으로 전환한다.
  - 완료: `삼번 -> 3번`, `알피엠 -> rpm`, `퍼센트/프로 -> percent`를 최소 규칙으로 추가했다.

완료 기준:

- [x] 샘플 장비 별칭이 표준 ID 후보로 변환된다.
- [x] 정규화 규칙은 짧고 명확하다.

---

### 6. 정책 엔진

- [x] 6.1 `policy_engine.py` 작성
  - 생성: `api/services/policy_engine.py`
  - 내용: `confirm_all`, risky, medium, low, invalid 처리
  - Jetson 테스트: decision별 단위 테스트
  - 설명: 자동 실행 판단은 한 파일에 모은다.
  - 완료: `decide_policy()`가 검증 실패/unknown/low는 reject, medium/risky/confirm_all은 confirm, 명시적으로 허용된 안전 고신뢰 명령만 execute로 분기한다.

- [x] 6.2 `emergency_stop` 우회 금지 테스트
  - 수정: `test_policy_engine.py`
  - 내용: `emergency_stop`도 정책을 우회하지 않음을 확인
  - Jetson 테스트: unit test
  - 설명: 안전 정책이 코드에 고정되어야 한다.
  - 완료: `emergency_stop` 이름이어도 risky intent는 정책 엔진을 우회하지 않고 confirm으로 귀결됨을 테스트했다.

- [x] 6.3 policy reason 정리
  - 수정: `policy_engine.py`
  - 내용: 사람이 읽을 수 있는 reason 문자열 사용
  - Jetson 테스트: reason 포함 여부 확인
  - 설명: 운영 로그와 디버깅을 쉽게 한다.
  - 완료: `unknown_intent`, `validation_failed: ...`, `low_confidence`, `medium_confidence_requires_confirmation`, `risky_intent_requires_confirmation`, `confirm_all_enabled`, `execution_allowed` reason을 테스트했다.

완료 기준:

- [x] 기본 모드에서 제어 명령은 항상 `confirm`이다.
- [x] invalid/unknown/low는 `reject`다.

---

### 7. LLM 결과 검증

- [x] 7.1 `result_validator.py` 기본 작성
  - 생성: `api/services/result_validator.py`
  - 내용: LLM JSON의 intent, slots, confidence_score 파싱
  - Jetson 테스트: 정상 LLM 결과 테스트
  - 설명: LLM 결과를 신뢰하지 않고 항상 검증한다.
  - 완료: 문자열 JSON 또는 dict 형태의 LLM 결과를 받아 `ValidatedResult`로 변환하고, confidence score에서 high/medium/low를 산출한다.

- [x] 7.2 정의 외 intent 차단
  - 수정: `result_validator.py`
  - 내용: schema에 없는 intent는 `unknown`
  - Jetson 테스트: hallucinated intent 테스트
  - 설명: LLM 환각이 실행 정책으로 넘어가지 않게 한다.
  - 완료: schema에 없는 intent는 `intent="unknown"`, `is_valid=False`, 사람이 읽을 수 있는 오류 reason으로 반환한다.

- [x] 7.3 필수 slot 검증
  - 수정: `result_validator.py`
  - 내용: 필수 slot 누락, null 처리, `machine_id`/`component_id` 기본값 처리
  - Jetson 테스트: 누락 케이스 테스트
  - 설명: 필수 값 없이는 실행 가능한 결과가 아니다.
  - 완료: 필수 slot 누락은 invalid로 처리하고, 단일 장비 환경의 `machine_id`와 schema default가 있는 `component_id`는 기본값으로 채운다.

- [x] 7.4 타입/단위/범위 검증
  - 수정: `result_validator.py`
  - 내용: number/string/enum, min/max, required capability, target scope/component type 검증
  - Jetson 테스트: 범위 초과, enum 오류 테스트
  - 설명: 공장 제어에서는 값 범위 검증이 핵심 안전 장치다.
  - 완료: string/boolean/integer/number/enum 타입, min/max 범위, equipment/component capability, component type mismatch를 검증한다.

완료 기준:

- [x] 잘못된 LLM 결과는 `is_valid=False`로 반환된다.
- [x] 검증 오류가 사람이 읽기 쉬운 문자열로 남는다.

---

### 8. Prompt 빌더

- [x] 8.1 시스템 프롬프트 작성
  - 생성: `api/services/prompt_builder.py`
  - 내용: JSON only, 후보 intent만 선택, decision 금지
  - Jetson 테스트: 문자열 포함 여부 테스트
  - 설명: LLM 역할을 좁게 제한한다.
  - 완료: `build_system_prompt()`가 JSON only, 후보 intent 제한, `intent/slots/confidence_score`만 반환, decision 금지를 명시하도록 작성했고 문자열 계약 테스트를 추가했다.

- [x] 8.2 후보 block 작성
  - 수정: `prompt_builder.py`
  - 내용: intent 이름, 설명, slot schema, seed utterance 포함
  - Jetson 테스트: 후보 0개/1개/여러 개 테스트
  - 설명: 사람이 읽어도 prompt 구조를 이해할 수 있어야 한다.
  - 완료: `build_candidate_block()`이 후보 intent의 이름, 설명, target scope, capability, slot schema, seed utterance를 구조화해 출력하고, 후보 없음/단일/복수/unknown 후보 제외 케이스를 테스트했다.

- [x] 8.3 device 후보 포함
  - 수정: `prompt_builder.py`
  - 내용: normalizer가 찾은 equipment/component 후보와 capability 정보 전달
  - Jetson 테스트: device/component candidate 포함 여부 확인
  - 설명: 장비 ID와 component ID 추정을 안정화한다.
  - 완료: `build_device_block()`이 normalizer가 찾은 device/component 후보의 id, type, alias, capability 정보를 구조화해 출력하고, 빈 후보/equipment 후보/component 후보 케이스를 테스트했다.

완료 기준:

- [x] LLM prompt가 짧고 구조적이다.
- [x] decision 판단을 LLM에 요구하지 않는다.

---

### 9. 외부 클라이언트

- [x] 9.1 embedder client 작성
  - 생성: `api/services/embedder_client.py`
  - 내용: TEI `/embed` 호출 wrapper
  - Jetson 테스트: httpx mock 테스트
  - 설명: 실제 TEI는 x86 GPU 서버에서 검증한다.
  - 완료: `EmbedderClient`가 TEI `/embed`에 `inputs` payload를 POST하고 embedding 응답을 float list로 검증한다. HTTP 오류, 잘못된 JSON shape, 단일 embedding 개수 오류를 명확한 `EmbedderClientError`로 처리하도록 mock 테스트했다.

- [x] 9.2 LLM client 작성
  - 생성: `api/services/llm_client.py`
  - 내용: `httpx` 기반 OpenAI-compatible `/chat/completions` 호출
  - Jetson 테스트: `httpx.Client.post` mock 테스트
  - 설명: Qwen3.5 계열 OpenAI-compatible 서버를 우선 염두에 두되, 의존성을 줄이기 위해 LangChain adapter 대신 직접 HTTP 호출을 사용한다.
  - 완료: `LLMClient`가 OpenAI-compatible `/chat/completions` endpoint에 system/user message payload를 POST하고 텍스트 content를 반환한다. 단위 테스트는 request payload, auth header, JSON 파싱, 오류 래핑을 검증했다.

- [x] 9.3 timeout 처리 작성
  - 수정: `llm_client.py`, `embedder_client.py`
  - 내용: timeout 시 명확한 예외 또는 reject 가능한 결과로 변환
  - Jetson 테스트: timeout mock 테스트
  - 설명: 외부 장애가 서버 전체 장애로 번지지 않게 한다.
  - 완료: `EmbedderClient`는 `httpx.TimeoutException`을 `embedder request timed out`으로, 기타 `httpx.RequestError`를 명확한 요청 실패로 변환한다. `LLMClient`는 `httpx.TimeoutException`을 `llm request timed out`으로 분리하고, 기타 `httpx.RequestError`는 `llm request failed: ...`로 감싼다. 서버 오류와 일시적 네트워크 오류는 `LLM_MAX_RETRIES` 범위에서 재시도한다.

완료 기준:

- [x] 외부 호출은 모두 mock으로 테스트 가능하다.
- [x] 네트워크 오류 메시지가 명확하다.

---

### 10. FAISS VectorStore

- [x] 10.1 VectorStore 기본 작성
  - 생성: `api/services/vector_store.py`
  - 내용: embedding 배열과 metadata로 index build/search
  - Jetson 테스트: 작은 numpy 배열로 검색 테스트
  - 설명: FAISS 사용 코드를 작게 격리한다.
  - 완료: `VectorStore.build()`와 `search()`를 추가했다. x86에서 `faiss-cpu`가 있으면 `IndexFlatIP`를 사용하고, Jetson/unit test에서는 numpy fallback으로 동일한 cosine 검색 계약을 검증한다.

- [x] 10.2 seed metadata 구성
  - 수정: `schema_manager.py` 또는 `vector_store.py`
  - 내용: seed utterance와 intent metadata 연결
  - Jetson 테스트: metadata 매핑 테스트
  - 설명: 검색 결과가 어떤 intent에서 왔는지 명확해야 한다.
  - 완료: `SchemaManager.list_seed_records()`가 seed utterance별 intent, risk, target scope, capability, component type metadata를 반환하고, `VectorStore` 검색 결과가 해당 metadata를 보존하는지 테스트했다.

- [x] 10.3 인덱스 빌드 스크립트 작성
  - 생성: `scripts/build_index.py`
  - 내용: seed utterance 로드, embedder 호출, index 저장
  - Jetson 테스트: embedder mock 모드 또는 dry-run
  - x86 테스트: 실제 TEI로 인덱스 생성
  - 설명: 실제 embedding 생성은 x86 GPU 서버에서 확인한다.
  - 완료: `scripts/build_index.py`가 schema seed records를 로드하고, 실제 `EmbedderClient` 또는 `--mock-embeddings`로 embedding을 생성해 `VectorStore`를 `.npz`로 저장한다. Jetson에서는 mock embedding과 `--no-faiss`로 저장/로드 경로를 검증했다.

완료 기준:

- [x] unit test에서 검색 결과 순서와 metadata가 맞다.
- [x] 실제 인덱스 생성은 x86 GPU 서버 검증 대상으로 남긴다.

---

### 11. 파이프라인 조립

- [x] 11.1 `pipeline.py` skeleton 작성
  - 생성: `api/services/pipeline.py`
  - 내용: 의존성 주입 가능한 `classify` 함수 구조
  - Jetson 테스트: 모든 의존성 mock으로 정상 흐름 테스트
  - 설명: 실제 외부 호출 없이 흐름을 검증한다.
  - 완료: `ClassificationPipeline`과 `PipelineDependencies`를 추가해 normalize/classify/policy 단계를 주입받도록 만들고, mock dependency로 `ClassifyResponse` 조립을 테스트했다.

- [x] 11.2 정상 classify 흐름 연결
  - 수정: `pipeline.py`
  - 내용: normalize -> embed -> search -> prompt -> llm -> validate -> policy
  - Jetson 테스트: 정상 응답 테스트
  - 설명: 한 번에 실제 서비스 연결을 하지 않는다.
  - 완료: `build_classify_normalized()`가 embedder, vector store, prompt builder, LLM client, result validator를 연결하고, `ClassificationPipeline`에서 policy까지 이어지는 정상 `confirm` 응답을 mock 외부 의존성으로 테스트했다.

- [x] 11.3 실패 흐름 연결
  - 수정: `pipeline.py`
  - 내용: embedder 실패, LLM timeout, validation 실패
  - Jetson 테스트: 실패 케이스별 테스트
  - 설명: 실패가 `reject` 또는 명확한 오류로 귀결되어야 한다.
  - 완료: embedder/vector search 오류와 LLM 오류는 invalid `ValidatedResult`로 변환해 reject 경로를 타게 했고, validation 실패는 정책 엔진의 `validation_failed` reject로 귀결되도록 테스트했다.

완료 기준:

- [x] mock 기반 pipeline test가 통과한다.
- [x] 기본 제어 명령은 `confirm`으로 반환된다.

---

### 12. FastAPI 라우터

- [x] 12.1 health 라우터 작성
  - 생성: `api/routers/health.py`
  - 엔드포인트: `/health`, `/ready`, `/metrics`
  - Jetson 테스트: TestClient 테스트
  - 설명: `/ready`는 schema/index/외부 설정 상태를 반영한다.
  - 완료: 기존 `/health`에 `/ready`, `/metrics`를 추가했다. `/ready`는 `app.state`의 schema/index/settings 상태를 반영하고, `/metrics`는 Prometheus payload를 반환한다. Jetson 환경에서 TestClient가 멈춰 라우터 함수 단위 테스트로 응답 계약을 검증했다.

- [x] 12.2 classify 라우터 작성
  - 생성: `api/routers/classify.py`
  - 엔드포인트: `POST /v1/classify`
  - Jetson 테스트: TestClient + mock pipeline
  - 설명: API 계층은 얇게 유지한다.
  - 완료: `POST /v1/classify` 라우터를 추가해 `app.state.pipeline.classify()`만 호출하도록 만들고, pipeline 미준비 시 503을 반환하도록 함수 단위 테스트했다.

- [x] 12.3 main 앱 연결
  - 수정: `api/main.py`
  - 내용: 라우터 등록, middleware 등록 위치 확보
  - Jetson 테스트: 앱 import와 route 존재 확인
  - 설명: 앱 생성 로직이 복잡해지지 않게 한다.
  - 완료: `create_app()`이 health/classify 라우터를 등록하고, settings/schema/vector_store/pipeline state를 선택적으로 주입받도록 만들었다. 앱 import, route 존재, runtime state 주입을 테스트했다.

완료 기준:

- [x] `POST /v1/classify`가 mock pipeline으로 응답한다.
- [x] `/health`가 200을 반환한다.

---

### 13. 인증, 로깅, 메트릭

- [x] 13.1 API token 인증 작성
  - 생성: `api/middleware/auth_mw.py`
  - 내용: `Authorization: Bearer <token>` 확인
  - Jetson 테스트: 토큰 없음/오류/정상 테스트
  - 설명: 내부망이라도 API 인증은 필수다.
  - 완료: `auth_middleware`와 `configure_auth()`를 추가했다. token이 설정된 경우 protected path는 `Authorization: Bearer <token>`을 요구하고, `/health`, `/ready`, `/metrics`는 public path로 유지한다. 토큰 없음/오류/정상과 `create_app()` 연결을 테스트했다.

- [x] 13.2 구조화 로깅 작성
  - 생성: `api/middleware/logging_mw.py`
  - 내용: request id, decision, intent, latency, error
  - Jetson 테스트: 로그 필드 테스트
  - 설명: 원문 발화는 기본 저장하지 않는다.
  - 완료: `logging_middleware`와 `configure_logging()`을 추가했다. request id, method, path, status code, latency, error class를 구조화 필드로 남기고, 원문 발화/body는 기록하지 않는다. 응답에는 `x-request-id`를 설정한다.

- [x] 13.3 Prometheus 메트릭 작성
  - 생성: `api/middleware/metrics_mw.py`
  - 내용: request count, latency, decision count, timeout count
  - Jetson 테스트: `/metrics` 응답 포함 여부
  - 설명: 운영 관측에 필요한 최소 메트릭만 둔다.
  - 완료: `metrics_middleware`와 `configure_metrics()`를 추가했다. HTTP request count/latency, classify decision count, external timeout count를 앱별 Prometheus registry에 기록하고 `/metrics`에서 해당 registry를 반환하도록 연결했다.

완료 기준:

- [x] 인증 없는 요청은 거부된다.
- [x] 로그에 원문 발화가 기본 저장되지 않는다.
- [x] `/metrics`가 Prometheus 형식으로 응답한다.

---

### 14. Docker와 실행 스크립트

- [x] 14.1 Dockerfile 작성
  - 생성: `docker/Dockerfile`
  - 내용: FastAPI 앱 실행 이미지
  - Jetson 테스트: 문법 검토
  - x86 테스트: 실제 docker build
  - 설명: Docker 완료 기준은 x86 GPU 서버다.
  - 완료: repo root build context 기준 Dockerfile을 작성했다. `requirements-x86.txt`를 설치하고 `api/`, `data/`, `scripts/`를 복사한 뒤 `uvicorn main:app`으로 실행한다. Jetson에서는 파일 내용 검증 테스트만 수행했고, 실제 docker build는 x86 GPU 서버 검증으로 남긴다.

- [x] 14.2 build/run 스크립트 작성
  - 생성: `docker/build.sh`, `docker/run.sh`
  - 내용: intent-api 이미지 빌드와 API 컨테이너 실행
  - Jetson 테스트: shellcheck 가능 시 확인, 아니면 내용 검토
  - x86 테스트: 실제 실행
  - 설명: Reranker는 포함하지 않는다.
  - 완료: `docker/build.sh`, `docker/run.sh`, `docker/run_embedder.sh`, `scripts/build_index.sh`, `.env.example`을 추가했다. build script는 repo root context로 `intent-api:latest` 이미지를 만들고, run script는 repo root의 `.env`를 자동 로드한 뒤 9090 포트 기준으로 API 컨테이너를 실행한다. TEI embedder는 별도 컨테이너로 실행하고 기본 포트는 9091로 둔다. Host index 생성은 `HOST_EMBEDDER_URL`, API 컨테이너 호출은 `EMBEDDER_URL`로 분리했다.

- [x] 14.3 x86 서버 실행 절차 문서화
  - 수정: README 또는 별도 운영 메모
  - 내용: 수동 복사, docker build, index build, run
  - Jetson 테스트: 문서 검토
  - 설명: 원시적 수동 배포 과정을 숨기지 않는다.
  - 완료: `docs/X86_DEPLOYMENT.md`를 추가하고 README에 링크했다. 문서에는 소스 복사, `.env` 작성, TEI 별도 컨테이너 실행, seed index 생성, API image build/run, health/ready/metrics/classify 확인 명령을 정리했다. `main.py`의 runtime bootstrap이 schema, index, embedder, LLM client, pipeline을 자동 조립하는 기준도 명시했다.

완료 기준:

- [x] x86 GPU 서버에서 Docker build/run 시도 준비가 된다.

---

### 15. Jetson 통합 점검

- [x] 15.1 전체 unit test 실행
  - 대상: `tests/unit/`
  - Jetson 테스트: 전체 unit test
  - 설명: 실제 외부 서비스 없이 모든 핵심 로직을 검증한다.
  - 완료: `PYTHONPATH=api:. .venv/bin/pytest tests/unit`로 120개 unit test 통과를 확인했다.

- [x] 15.2 mock integration test 실행
  - 대상: `tests/integration/test_classify_api.py`
  - Jetson 테스트: TestClient + mock pipeline 또는 mock clients
  - 설명: API 입출력 형태를 확인한다.
  - 완료: TestClient 대신 router 함수 직접 호출 방식의 mock integration test를 추가했다. Runtime bootstrap, `/ready`, `/v1/classify` 응답 계약을 fake embedder/LLM과 임시 vector index로 검증한다.

- [x] 15.3 변경 파일 목록 정리
  - 대상: 신규/수정 파일 목록
  - Jetson 테스트: `rg --files`로 확인
  - 설명: x86 서버로 수동 복사할 파일을 명확히 한다.
  - 완료: `docs/X86_DEPLOYMENT.md`에 필수/권장/제외 배포 파일 목록을 정리했다.

완료 기준:

- [x] Jetson에서 가능한 테스트가 통과한다.
- [x] x86 서버로 전달할 파일 목록이 정리된다.

---

### 16. x86 GPU 서버 수동 테스트 절차 이관

- [x] 16.1 x86 서버 수동 테스트 절차를 `docs/X86_DEPLOYMENT.md`로 이관
  - 이관 위치: `docs/X86_DEPLOYMENT.md`
  - 포함 내용: 파일 복사, `.env` 작성, TEI 실행, seed index 생성, API image build/run, `/health`, `/ready`, `/metrics`, `/v1/classify` 확인
  - 설명: CODEX 환경이 없는 x86 서버에서는 코드 생성/수정 없이 문서 절차대로 설치, 실행, 테스트, 검증만 수행한다.

- [x] 16.2 x86 수동 검증 체크리스트 작성
  - 이관 위치: `docs/X86_DEPLOYMENT.md`의 "x86 수동 검증 체크리스트"
  - 설명: 실제 x86 검증 결과는 이 구현 계획 문서가 아니라 배포 문서에서 추적한다.

완료 기준:

- [x] 이 문서에 남아 있던 x86 실행 항목은 `docs/X86_DEPLOYMENT.md`로 이관되었다.
- [x] 이후 x86 서버 작업은 `docs/X86_DEPLOYMENT.md`를 기준으로 진행한다.

---

### 17. 피드백 반영 절차 이관

- [x] 17.1 피드백 분류 기준을 `docs/X86_DEPLOYMENT.md`로 이관
  - 이관 위치: `docs/X86_DEPLOYMENT.md`의 "피드백 기록 기준"
  - 분류: 환경 오류, 설정 오류, 데이터 오류, 코드 오류, LLM 응답 문제

- [x] 17.2 x86 서버에서 코드 수정 금지 원칙 명시
  - 설명: x86 서버에서는 설치, 테스트, 검증, 로그 기록만 수행한다. 코드 수정은 Codex 사용 가능 환경으로 돌아와 작은 단위로 수행한다.

완료 기준:

- [x] 피드백 기록과 후속 수정 절차는 `docs/X86_DEPLOYMENT.md`로 이관되었다.
- [x] 이 문서는 구현 완료 상태로 닫고, 이후 작업은 배포 문서에서 이어서 진행한다.

---

## 6. 체크박스 업데이트 규칙

- 단계 완료 시 해당 항목을 `[x]`로 바꾼다.
- 실패한 단계는 체크하지 않고 실패 원인을 바로 아래에 적는다.
- 질문 게이트에서 답이 필요한 경우 해당 단계에 `대기`라고 적는다.
- x86 서버에서만 확인 가능한 실제 실행 결과는 `docs/X86_DEPLOYMENT.md`에서 추적한다.
- 이 문서의 16/17단계 체크는 x86 실행 완료가 아니라 배포 문서로 절차 이관이 완료되었다는 의미다.

---

## 7. 문서 종료 기준

이 문서는 Codex 사용 가능 환경에서의 코드 생성, 문서 보완, unit/mock 검증 계획을 닫는다.

이후 작업 흐름:

- [x] Jetson/Codex 환경에서 가능한 구현과 검증은 완료했다.
- [x] x86 GPU 서버 배포와 실제 검증은 `docs/X86_DEPLOYMENT.md`로 이어서 진행한다.
- [x] x86 서버에서는 코드 수정 없이 설치, 실행, 테스트, 로그 기록만 수행한다.
