# PLAN_CODING.md: 구현 계획

## 1. 구현 원칙

- 코드는 단순하고 읽기 쉬운 구조를 우선한다.
- LLM은 후보 intent 선택과 slot JSON 작성만 담당한다.
- 최종 `decision`은 코드의 검증 로직과 정책 엔진이 결정한다.
- 기본 운영 모드에서는 모든 제어 명령을 `confirm`으로 반환한다.
- Reranker, fine-tuning, `/admin/reload`는 MVP에 포함하지 않는다.

---

## 2. 개발 및 테스트 환경

개발환경과 실사용 테스트/양산 환경은 다르다.

| 구분 | 개발환경 | 실사용 테스트/양산 환경 |
|---|---|---|
| 장비 | JETSON ORIN NX 16GB | Ubuntu Linux 20.04 x86 기반 NVIDIA GPU 서버 |
| 아키텍처 | ARM/aarch64 | x86_64 |
| 역할 | 코드 작성, 문서 수정, unit/mock 테스트 | Docker 실행, TEI 임베더, FAISS, 외부 LLM 연동, E2E/성능 테스트 |
| 완료 기준 | 코드 로직 검증 | 실사용 가능성 검증 |

작업 흐름:

1. Jetson에서 작은 단위로 코드를 작성한다.
2. Jetson에서 unit/mock 테스트를 수행한다.
3. 변경 파일을 x86 GPU 서버로 수동 복사한다.
4. x86 GPU 서버에서 빌드, 인덱스 생성, 실제 연동 테스트를 수행한다.
5. 서버 로그와 테스트 결과를 Jetson 개발환경에 반영한다.

의존성 기준:

- Jetson 개발환경은 Python 3.8 가상환경과 `api/requirements.txt`를 사용한다.
- x86 GPU 서버는 `api/requirements-x86.txt`를 사용해 FAISS 의존성을 추가한다.

---

## 3. 프로젝트 구조

```text
command-interpreter/
├── docker/
│   ├── Dockerfile
│   ├── build.sh
│   └── run.sh
├── api/
│   ├── requirements.txt
│   ├── requirements-x86.txt
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── common.py
│   │   ├── request.py
│   │   ├── response.py
│   │   └── schema.py
│   ├── routers/
│   │   ├── classify.py
│   │   └── health.py
│   ├── services/
│   │   ├── pipeline.py
│   │   ├── normalizer.py
│   │   ├── embedder_client.py
│   │   ├── vector_store.py
│   │   ├── llm_client.py
│   │   ├── prompt_builder.py
│   │   ├── schema_manager.py
│   │   ├── result_validator.py
│   │   └── policy_engine.py
│   └── middleware/
│       ├── auth_mw.py
│       ├── logging_mw.py
│       └── metrics_mw.py
├── data/
│   ├── intents.yaml
│   ├── devices.yaml
│   └── golden/
├── tests/
└── scripts/
```

---

## 4. 핵심 모듈

| 모듈 | 책임 |
|---|---|
| `config.py` | 환경 변수 로드 |
| `normalizer.py` | 발화 정규화, 장비/컴포넌트 별칭 해석 |
| `embedder_client.py` | TEI 임베더 호출 |
| `vector_store.py` | FAISS 인덱스 생성과 검색 |
| `prompt_builder.py` | 후보 intent 기반 LLM prompt 구성 |
| `llm_client.py` | 외부 LLM 호출과 timeout 처리 |
| `schema_manager.py` | `load_schema()` 진입점으로 intent/device YAML 로드와 검증 |
| `result_validator.py` | LLM 결과, slot, 값 범위 검증 |
| `policy_engine.py` | `execute` / `confirm` / `reject` 결정 |
| `pipeline.py` | 전체 흐름 조립 |

---

## 5. 파이프라인

```text
ClassifyRequest
  -> normalizer
  -> embedder_client
  -> vector_store.search
  -> prompt_builder
  -> llm_client
  -> result_validator
  -> policy_engine
  -> ClassifyResponse
```

정책 규칙:

```python
def decide(validation, mode):
    if not validation.is_valid:
        return reject(validation.errors)
    if validation.intent == "unknown":
        return reject(["unknown_intent"])
    if validation.confidence == "low":
        return reject(["low_confidence"])
    if mode == "confirm_all":
        return confirm(["confirm_all_control_commands"])
    if validation.is_risky:
        return confirm(["risky_intent"])
    if validation.confidence == "medium":
        return confirm(["medium_confidence"])
    return execute(["validated_non_risky_high_confidence"])
```

`emergency_stop`은 이 정책을 우회하지 않는다.

---

## 6. 설정

필수 환경 변수:

| 변수명 | 설명 |
|---|---|
| `LLM_API_URL` | 외부 LLM 서버 base URL |
| `API_AUTH_TOKEN` | 외부 LLM 사용 시 API 인증 토큰, 로컬 LLM은 선택 사항 |

주요 기본값:

| 변수명 | 기본값 |
|---|---|
| `LLM_MODEL_NAME` | `Qwen3.5-35B-A3B` |
| `LLM_TIMEOUT_MS` | `800` |
| `LLM_MAX_RETRIES` | `0` |
| `EMBEDDER_URL` | `http://embedder:80` |
| `FAISS_TOP_K` | `10` |
| `CONFIDENCE_HIGH` | `0.85` |
| `CONFIDENCE_LOW` | `0.60` |
| `POLICY_MODE` | `confirm_all` |
| `INTENT_SCHEMA_PATH` | `/app/data/intents.yaml` |
| `DEVICE_SCHEMA_PATH` | `/app/data/devices.yaml` |
| `RAW_UTTERANCE_LOGGING` | `false` |

---

## 7. 데이터 파일

### `data/intents.yaml`

```yaml
version: "1.0"

intents:
  - name: set_light_intensity
    description: "조명 밝기를 설정한다."
    target_scope: component
    target_component_type: led_light
    required_capability: light.intensity.set
    is_risky: false
    allowed_decisions: ["confirm", "reject", "execute"]
    slots:
      - name: machine_id
        type: string
        required: true
      - name: component_id
        type: string
        required: false
        default: "led_light"
      - name: value
        type: integer
        required: true
        min: 0
        max: 255
    seed_utterances:
      - "조명 밝기 250으로 올려"
      - "조명 150으로 맞춰"
```

### `data/devices.yaml`

```yaml
version: "1.0"

devices:
  - id: machine_inspection
    type: vision_inspection
    line: line_packaging
    aliases:
      - "비전 검사기"
      - "검사기"
    capabilities:
      - machine.start
      - machine.stop
      - machine.status.read
      - vision.model.change
    components:
      - id: led_light
        type: led_light
        aliases:
          - "조명"
          - "라이트"
        capabilities:
          - light.intensity.set
      - id: plc
        type: plc
        aliases:
          - "PLC"
          - "피엘씨"
        capabilities:
          - plc.status.read
          - plc.reset
          - plc.bring_in
          - plc.align
          - plc.up
          - plc.rotate
          - plc.down
          - plc.flip
          - plc.send_out
```

설계 기준:

- `devices.yaml`은 최상위 equipment와 하위 `components`를 함께 정의한다.
- `intents.yaml`은 특정 장비 ID가 아니라 `required_capability`를 요구한다.
- `target_scope: equipment`인 intent는 equipment capability로 검증한다.
- `target_scope: component`인 intent는 `target_component_type`과 component capability로 검증한다.
- PLC 동작 intent는 PLC가 수행 주체이고 제품이 대상이다. intent 이름은 `plc_bring_in`, `plc_align`, `plc_move_up`처럼 주체를 앞에 둔다.

---

## 8. Docker 기준

Docker 실행은 Ubuntu Linux 20.04 x86 기반 NVIDIA GPU 서버에서 수행한다.

컨테이너:

| 컨테이너 | 역할 |
|---|---|
| `intent-api` | FastAPI API 서버 |
| `embedder` | Qwen3-Embedding-0.6B TEI 서버 |

`docker/run.sh`는 다음 환경 변수를 받아 실행한다.

```bash
API_AUTH_TOKEN=change-me \
LLM_API_URL=http://10.0.1.50:8000/v1 \
./docker/run.sh
```

---

## 9. 구현 순서

| 순서 | 작업 |
|---:|---|
| 1 | 프로젝트 스캐폴딩과 설정 관리 작성 |
| 2 | Pydantic request/response/schema 모델 작성 |
| 3 | intent/device YAML 로더 작성 |
| 4 | normalizer 작성 |
| 5 | embedder client와 FAISS vector store 작성 |
| 6 | prompt builder와 LLM client 작성 |
| 7 | result validator 작성 |
| 8 | policy engine 작성 |
| 9 | pipeline과 `POST /v1/classify` 작성 |
| 10 | 인증, 로깅, 메트릭 작성 |
| 11 | unit/mock 테스트 작성 |
| 12 | x86 GPU 서버에서 통합 테스트 수행 |

---

## 10. 테스트 기준

Jetson에서 수행:

- `normalizer` unit test
- `schema_manager` unit test
- `result_validator` unit test
- `policy_engine` unit test
- 외부 의존성 mock 기반 `pipeline` test

x86 GPU 서버에서 수행:

- Docker 빌드와 실행
- 실제 TEI 임베딩 호출
- FAISS 인덱스 생성과 검색
- 외부 LLM 연동
- `/v1/classify`, `/ready`, `/metrics` 확인
- E2E 시나리오와 latency 측정

완료 기준:

- 기본 운영 모드에서 제어 명령은 `confirm`
- 위험 명령은 항상 `confirm`
- OOD와 검증 실패는 `reject`
- critical false execute 0건
- P95 latency 목표 충족 여부 측정

---

## 11. 수동 테스트 흐름

```text
Jetson 개발환경
  1. 코드 작성
  2. unit/mock 테스트
  3. 변경 파일 정리

x86 GPU 서버
  4. 변경 파일 수동 복사
  5. Docker 이미지 재빌드
  6. 인덱스 재빌드
  7. API와 메트릭 테스트
  8. 로그, 오류, latency 기록

Jetson 개발환경
  9. 피드백 반영
```
