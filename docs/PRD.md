# PRD: 공장 음성 제어용 Command Interpreter

## 1. 목적

Command Interpreter는 STT 결과 텍스트를 받아 공장 장비 제어 의도를 구조화된 JSON으로 해석하는 컴포넌트다.

이 컴포넌트는 제어 API를 직접 호출하지 않는다. 실제 실행, 재확인 UX, 권한 판단, 비상 정지 안전 경로는 오케스트레이터와 설비 안전 시스템이 담당한다.

핵심 원칙:

- 초기 지원 범위는 20~30개 핵심 intent로 제한한다.
- 모든 제어 명령은 기본적으로 `confirm`을 반환한다.
- LLM은 후보 intent 선택과 slot 추출만 담당한다.
- 최종 `decision`은 코드의 스키마 검증과 정책 엔진이 결정한다.
- 명확성, 안전성, 유지보수성을 성능 최적화보다 우선한다.

---

## 2. 범위

### 포함

- 한국어 발화 텍스트의 intent 분류
- slot 추출
- 장비명/별칭 정규화
- confidence 산출
- `execute` / `confirm` / `reject` 결정
- 위험 명령 여부(`is_risky`) 반환
- REST API, 구조화 로깅, Prometheus 메트릭

### 제외

- STT 처리
- 제어 API 라우팅 및 호출
- 재확인 UX 구현
- 물리/PLC 비상 정지 경로
- 외부 LLM 서버 운영
- 다국어 지원
- Reranker, fine-tuning, 무중단 admin reload

---

## 3. 시스템 구조

```text
STT 텍스트
  -> 정규화 / 장비명 해석
  -> BGE-M3 임베딩
  -> FAISS Top-K 검색
  -> 외부 LLM 후보 선택 + slot 추출
  -> 스키마 검증 / 값 범위 검증
  -> 정책 엔진 decision 결정
  -> JSON 응답
```

구성 요소:

| 구성 요소 | 책임 |
|---|---|
| `intent-api` | REST API, 파이프라인 조립, 로깅, 메트릭 |
| `normalizer` | 발화 정규화, 장비/컴포넌트 별칭을 표준 ID 후보로 변환 |
| `embedder` | BGE-M3 임베딩 생성 |
| FAISS | 시드 발화 기반 Top-K 후보 검색 |
| 외부 LLM | 후보 중 intent 선택, slot JSON 작성 |
| `result_validator` | intent, slot, 단위, 값 범위 검증 |
| `policy_engine` | `execute` / `confirm` / `reject` 결정 |

---

## 4. API

### `POST /v1/classify`

요청:

```json
{
  "session_id": "ses-001",
  "operator_id": "op-042",
  "utterance": "검사기 조명 200으로 맞춰"
}
```

응답:

```json
{
  "session_id": "ses-001",
  "decision": "confirm",
  "intent": "set_light_intensity",
  "slots": {
    "machine_id": "machine_inspection",
    "component_id": "led_light",
    "value": 200
  },
  "confidence": "high",
  "confidence_score": 0.92,
  "is_risky": false,
  "policy_reasons": ["confirm_all_control_commands"],
  "processing_time_ms": 185
}
```

### 운영 엔드포인트

| 엔드포인트 | 역할 |
|---|---|
| `GET /health` | 프로세스 liveness |
| `GET /ready` | 스키마, 인덱스, 외부 LLM 설정 상태 |
| `GET /metrics` | Prometheus 메트릭 |

---

## 5. Decision 정책

| decision | 조건 | 호출 측 처리 |
|---|---|---|
| `execute` | 제한 실행 모드에서 high confidence, non-risky, 모든 필수 slot 유효, 값 범위 유효 | 즉시 실행 가능 |
| `confirm` | 기본 운영 모드의 모든 제어 명령, risky 명령, medium confidence | 운영자 재확인 후 실행 |
| `reject` | low confidence, OOD, 정의 외 intent, 필수 slot 누락, 타입/단위/값 범위 오류 | 재발화 또는 수동 제어 유도 |

기본 운영 모드에서는 모든 제어 명령을 `confirm`으로 반환한다. `execute`는 검증된 non-risky 명령에 대해서만 별도 정책으로 허용한다.

---

## 6. 기능 요구사항

| ID | 요구사항 |
|---|---|
| FR-1 | 지원 intent는 초기 20~30개 핵심 명령으로 제한한다. |
| FR-2 | 정의되지 않았거나 불명확한 발화는 `unknown` + `reject`로 처리한다. |
| FR-3 | intent별 필수 slot, 선택 slot, 타입, 단위, 값 범위를 검증한다. |
| FR-4 | 장비 및 하위 컴포넌트 별칭과 STT 오인식 표현을 표준 ID 후보로 정규화한다. |
| FR-5 | LLM이 정의 외 intent를 반환하면 `unknown`으로 강등한다. |
| FR-6 | `medium` confidence는 자동 실행하지 않는다. |
| FR-7 | `is_risky: true` intent는 항상 `confirm` 이상으로 제한한다. |
| FR-8 | 원문 발화와 운영자 식별자는 기본적으로 마스킹 또는 해시 처리한다. |

---

## 7. 비기능 요구사항

### 성능

- 초기 P95 latency 목표: 500ms 이하
- 제한 실행 모드 목표: 250ms 이하
- 동시 처리 기준: 5 requests
- Peak QPS 기준: 10

### 보안

- 내부망 사용을 전제로 하되 API 인증은 필수다.
- 인증 방식은 static token 또는 mTLS 중 하나를 사용한다.
- 외부 노출 포트는 API 포트 하나로 제한한다.
- 로그 접근 권한과 보관 기간을 운영 정책으로 관리한다.

### 관측성

메트릭:

- 요청 수
- latency 분포
- intent별 빈도
- confidence 분포
- decision 분포
- reject/confirm 비율
- LLM 응답 시간과 timeout 수

---

## 8. 데이터 스키마

Intent 스키마 필수 항목:

- `name`
- `description`
- `target_scope` (`equipment` 또는 `component`)
- `required_capability`
- `target_component_type` (`target_scope: component`인 경우)
- `is_risky`
- `slots`
- `allowed_decisions`
- `seed_utterances`

Slot 스키마 필수 항목:

- `name`
- `type`
- `required`
- `values` 또는 `min`/`max` (필요 시)
- `default` (필요 시)

장비 스키마 필수 항목:

- `id`
- `type`
- `line`
- `aliases`
- `capabilities`
- `components`

장비는 equipment 레벨의 최상위 단위로 등록한다. 예를 들어 `machine_inspection`은 하나의 비전검사기 장비이고, `camera`, `led_light`, `robot`, `plc`는 해당 장비의 하위 컴포넌트다. intent는 특정 장비 ID 대신 `required_capability`를 요구하고, 장비 또는 컴포넌트가 그 capability를 제공하는지 검증한다.

PLC 관련 명령은 PLC가 수행 주체이고 `제품`이 동작 대상이다. 예: `plc_bring_in`, `plc_align`, `plc_move_up`, `plc_rotate`, `plc_move_down`, `plc_flip`, `plc_send_out`.

---

## 9. 안전 정책

- 비상 정지는 음성 LLM 경로에서 우회 실행하지 않는다.
- `emergency_stop` 의도는 신호로 반환할 수 있지만, 실제 비상 정지는 물리 버튼, PLC, 오케스트레이터 안전 경로가 담당한다.
- 필수 slot 누락, 정의 외 intent, 값 범위 초과, LLM timeout은 실행 가능한 결과로 반환하지 않는다.
- 위험 명령은 confidence가 높아도 재확인 대상이다.

---

## 10. 라이센스

| 항목 | 라이센스 |
|---|---|
| BAAI/bge-m3 | MIT |
| Qwen3-Reranker-0.6B | Apache 2.0 |
| Qwen3.5-35B-A3B | Apache 2.0 |
| FAISS | MIT |
| HuggingFace TEI | Apache 2.0 |

EXAONE 계열 모델은 라이센스 제약으로 사용하지 않는다.

---

## 11. 용어

| 용어 | 정의 |
|---|---|
| Intent | 제어 명령의 분류 |
| Slot | 명령 실행에 필요한 파라미터 |
| OOD | 정의된 범위를 벗어난 입력 |
| Confirm | 실행 전 운영자 재확인이 필요한 상태 |
| 오케스트레이터 | 분류 결과를 받아 제어 API를 라우팅·실행하는 상위 시스템 |
