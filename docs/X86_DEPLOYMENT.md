# x86 GPU Server Deployment

이 문서는 Ubuntu Linux x86_64 NVIDIA GPU 서버에서 RAIC intent API를 수동으로 실행하기 위한 절차다.

Jetson 개발환경에서는 unit/mock 테스트만 수행하고, Docker, TEI, FAISS, 외부 LLM 연동은 x86 GPU 서버에서 확인한다.

## 1. 전제

- Docker가 설치되어 있다.
- NVIDIA Container Toolkit이 설치되어 있고 `docker run --gpus all ...`을 사용할 수 있다.
- 사내망에서 OpenAI-compatible LLM 서버에 접근할 수 있다.
- TEI embedder는 API 컨테이너와 별도 컨테이너로 실행한다.
- Reranker는 MVP 범위에 포함하지 않는다.

포트 기준:

| 서비스 | 기본 포트 |
|---|---:|
| intent-api | 9090 |
| TEI embedder | 9091 |

## 2. 소스 복사

서버에 repository를 복사하거나 clone한다.

```bash
cd /opt
git clone <repo-url> raic
cd /opt/raic
```

수동 복사 환경이면 아래 배포 파일 목록을 함께 복사한다.

필수:

- `api/`
- `data/`
- `scripts/`
- `docker/`
- `.env.example`
- `README.md`

권장:

- `docs/`
- `tests/`

제외:

- `.env`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`

## 3. 환경 변수 파일 작성

```bash
cp .env.example .env
```

`.env`에서 서버 환경에 맞게 값을 수정한다.

```env
LLM_API_URL=http://10.0.1.50:8000/v1
LLM_API_KEY=
API_AUTH_TOKEN=change-me
EMBEDDER_URL=http://host.docker.internal:9091
HOST_EMBEDDER_URL=http://localhost:9091
TEI_HOST_PORT=9091
TEI_CONTAINER_PORT=80
TEI_IMAGE=ghcr.io/huggingface/text-embeddings-inference:latest
EMBEDDING_MODEL_ID=Qwen/Qwen3-Embedding-0.6B
VECTOR_INDEX_PATH=/app/data/seed_index.npz
HOST_VECTOR_INDEX_PATH=data/seed_index.npz
VECTOR_INDEX_USE_FAISS=true
HOST_PORT=9090
CONTAINER_PORT=9090
```

주의:

- `.env`는 실제 운영값을 담으므로 Git에 커밋하지 않는다.
- `LLM_API_URL`은 intent-api 컨테이너 내부에서 접근 가능한 사내망 주소여야 한다.
- LLM 서버 인증이 필요하면 `LLM_API_KEY`에 별도로 입력한다.
- `API_AUTH_TOKEN`은 RAIC API 호출을 보호하는 inbound bearer token이다.
- API 컨테이너가 같은 서버의 TEI 호스트 포트로 붙을 때는 `EMBEDDER_URL=http://host.docker.internal:9091`을 사용한다.
- host에서 index를 만들 때는 `HOST_EMBEDDER_URL=http://localhost:9091`을 사용한다.
- Docker network로 두 컨테이너를 묶는 경우에는 `EMBEDDER_URL=http://tei-embedder:80`처럼 컨테이너 이름을 사용할 수 있다.

## 4. TEI embedder 실행

TEI embedder는 별도 컨테이너로 실행한다. 이미지 태그와 모델 ID는 x86 서버에서 사용할 embedding 모델에 맞춰 `.env`에서 고정한다.

```bash
docker/run_embedder.sh
```

TEI가 이미 다른 방식으로 실행 중이라면 `.env`의 `EMBEDDER_URL`만 해당 주소로 맞춘다.

## 5. Seed index 생성

API가 FAISS 검색에 사용할 seed utterance index를 생성한다.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r api/requirements-x86.txt
scripts/build_index.sh
```

생성 결과:

```text
data/seed_index.npz
```

`docker/run.sh`는 host의 `data/` 디렉터리를 컨테이너의 `/app/data`로 read-only mount한다. 따라서 위 파일은 컨테이너 내부에서 `/app/data/seed_index.npz`로 보인다.

## 6. API 이미지 빌드

```bash
docker/build.sh
```

`.env.example` 기준 기본 이미지:

```text
intent-api:v0
```

`docker/build.sh`도 repository root의 `.env`를 자동으로 로드한다. `.env`가 없으면 script fallback은 `intent-api:latest`다. 이미지 이름이나 태그를 바꾸려면 `.env` 또는 shell 환경 변수에서 `IMAGE_NAME`, `IMAGE_TAG`를 지정한다.

## 7. API 컨테이너 실행

```bash
docker/run.sh
```

`docker/run.sh`는 repository root의 `.env`를 자동으로 로드한다.
Linux Docker에서 API 컨테이너가 호스트의 TEI 포트에 접근할 수 있도록 `host.docker.internal`을 `host-gateway`로 매핑한다.
또한 host의 `data/`를 `/app/data`로 mount하므로, `intents.yaml`, `devices.yaml`, `seed_index.npz`가 컨테이너에서 동일하게 사용된다.

실행 후 확인:

```bash
curl http://localhost:9090/health
curl http://localhost:9090/ready
curl http://localhost:9090/metrics
```

인증 토큰을 설정한 경우 classify 요청은 bearer token을 포함해야 한다.

```bash
curl -X POST http://localhost:9090/v1/classify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer change-me" \
  -d '{"utterance":"검사 시작해","session_id":"manual-x86-test","operator_id":"operator-1"}'
```

`API_AUTH_TOKEN`을 비워서 실행한 경우에는 `Authorization` header를 생략한다.

## 8. Runtime bootstrap

컨테이너 시작 시 `main.py`는 환경 변수 기준으로 다음 항목을 자동 조립한다.

- `Settings`
- intent/device YAML schema
- `VectorStore` from `/app/data/seed_index.npz`
- TEI `EmbedderClient`
- LangChain 기반 LLM client
- classification pipeline

`/ready`가 `ok`이면 schema, index, settings, pipeline 조립이 완료된 상태다. `not_ready`이면 응답의 `checks`와 `bootstrap_error`를 먼저 확인한다.

## 9. 문제 확인 명령

```bash
docker ps
docker logs intent-api
docker logs tei-embedder
curl http://localhost:9090/health
curl http://localhost:9090/ready
curl http://localhost:9091/embed \
  -H "Content-Type: application/json" \
  -d '{"inputs":["검사 시작"]}'
```

## 10. x86 수동 검증 체크리스트

아래 항목은 이 문서에서만 추적한다. `docs/PLAN_DETAILED_ACTION.md`의 16단계 이후 작업은 여기로 이관되었다.

- [ ] repository 또는 필수 파일 복사 완료
- [ ] `.env.example`을 `.env`로 복사하고 서버 값 반영
- [ ] `docker/run_embedder.sh` 실행
- [ ] `curl http://localhost:9091/embed ...`로 TEI 응답 확인
- [ ] `python3 -m venv .venv` 및 `pip install -r api/requirements-x86.txt` 완료
- [ ] `scripts/build_index.sh`로 `data/seed_index.npz` 생성
- [ ] `docker/build.sh`로 `intent-api` 이미지 빌드
- [ ] `docker/run.sh`로 API 컨테이너 실행
- [ ] `curl http://localhost:9090/health` 확인
- [ ] `curl http://localhost:9090/ready`가 `ok`인지 확인
- [ ] `curl http://localhost:9090/metrics` 확인
- [ ] `POST /v1/classify` 샘플 요청이 `confirm` 또는 안전한 `reject`로 응답하는지 확인
- [ ] latency, timeout, LLM 오류, slot 오류 사례 기록

## 11. 피드백 기록 기준

배포 후 문제가 생기면 x86 서버에서 코드를 수정하지 않는다. 아래 기준으로 기록한 뒤, Codex 사용 가능 환경으로 돌아와 작은 단위로 수정한다.

| 분류 | 기록할 내용 |
|---|---|
| 환경 오류 | Docker, NVIDIA runtime, port, network, file mount 문제 |
| 설정 오류 | `.env`, LLM URL, TEI URL, token, model id 문제 |
| 데이터 오류 | `intents.yaml`, `devices.yaml`, seed utterance, index 생성 문제 |
| 코드 오류 | traceback, failing endpoint, 재현 payload |
| LLM 응답 문제 | raw 응답 형태, 잘못된 intent/slot, confidence score |

최소 기록:

- 실행한 명령
- 실패한 시각
- 관련 로그: `docker logs intent-api`, `docker logs tei-embedder`
- `/ready` 응답
- classify 요청 payload와 응답
