# Device Onboarding Guide

새 라인, 장비, 컴포넌트를 추가할 때는 `data/devices.yaml`을 먼저 갱신하고, 필요한 경우에만 `data/intents.yaml`을 확장한다.

## 1. 추가 대상 구분

- 라인만 추가: 기존 장비와 같은 기능을 다른 라인에서 운영하는 경우
- 장비 추가: 새로운 equipment 단위가 생기는 경우
- 컴포넌트 추가: 기존 장비 아래에 카메라, 조명, 로봇, PLC 같은 하위 대상이 추가되는 경우
- 신규 명령 추가: 기존 intent와 capability로 표현할 수 없는 새 동작이 생기는 경우

## 2. `devices.yaml` 작성 규칙

장비는 최상위 `devices` 항목으로 추가한다.

```yaml
devices:
  - id: box_former
    line_id: line_s01
    line_aliases:
      - "S01"
      - "S01 라인"
    aliases:
      - "박스 제함기"
      - "제함기"
    capabilities:
      - machine.status.read
    components:
      - id: camera
        aliases:
          - "카메라"
        capabilities:
          - camera.gain.set
```

주의:

- `line_id`는 표준 ID다. 사용자 발화 표현은 `line_aliases`에 넣는다.
- `aliases`에는 장비명만 넣는다. `"S01 라인 박스 제함기"`처럼 라인명과 장비명이 결합된 표현은 피한다.
- `components[].id`는 컴포넌트 표준 ID다.
- 컴포넌트 식별은 `component_id`와 capability로만 한다. 별도 `type` 필드는 사용하지 않는다.
- 같은 장비 안에서 component `id`는 중복되면 안 된다.

## 3. Capability 확인

기존 intent를 재사용하려면 장비 또는 컴포넌트가 해당 intent의 `required_capability`를 가져야 한다.

예:

- 장비 상태 조회: 장비 `capabilities`에 `machine.status.read`
- 카메라 gain 설정: 카메라 component `capabilities`에 `camera.gain.set`
- 로봇 속도 설정: 로봇 component `capabilities`에 `robot.speed.set`

기존 capability로 표현할 수 없으면 `data/intents.yaml`에 신규 intent와 slot을 추가한다.

## 4. Intent 추가가 필요한 경우

`data/intents.yaml`에 새 intent를 추가할 때는 반드시 다음 slot을 포함한다.

```yaml
slots:
  - name: machine_id
    type: string
    required: true
  - name: line_id
    type: string
    required: true
```

컴포넌트 대상 명령이면 `component_id`도 포함한다.

```yaml
  - name: component_id
    type: string
    required: false
    default: "camera"
```

`seed_utterances`도 함께 추가한다. intent seed를 바꾸면 vector index를 다시 생성해야 한다.

## 5. 검증 순서

로컬에서 아래 명령을 실행한다.

```bash
PYTHONPATH=api .venv/bin/python -m pytest tests/unit/test_data_files.py tests/unit/test_schema_manager.py tests/unit/test_normalizer.py -q
```

전체 확인이 필요하면 다음을 실행한다.

```bash
PYTHONPATH=api .venv/bin/python -m pytest tests/unit tests/integration -q
```

## 6. Index와 배포

- `devices.yaml`만 바꾼 경우: API 재시작이 필요하다. seed index 재생성은 보통 필요 없다.
- `intents.yaml`의 `seed_utterances`를 바꾼 경우: `scripts/build_index.sh`로 `data/seed_index.npz`를 다시 만든다.
- Docker 배포 환경에서는 `data/`가 컨테이너에 mount되므로 파일 반영 후 API 컨테이너를 재시작한다.

## 7. 수동 확인 예시

새 장비를 추가한 뒤 대표 발화 2~3개를 정해 `POST /v1/classify`로 확인한다.

확인할 항목:

- `line_id`가 의도한 라인 표준 ID인지
- `machine_id`가 의도한 장비 표준 ID인지
- 컴포넌트 명령이면 `component_id`가 맞는지
- capability 누락으로 `validation_failed`가 발생하지 않는지
- risky intent가 `confirm`으로 반환되는지
