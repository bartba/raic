# RAIC Command Interpreter

공장 음성 제어 환경에서 STT 결과 텍스트를 구조화된 명령 후보로 해석하는 Command Interpreter 프로젝트입니다.

이 컴포넌트는 제어 API를 직접 호출하지 않습니다. 입력 발화에서 intent와 slot을 추출하고, 코드 기반 검증과 정책 판단을 거쳐 `execute`, `confirm`, `reject` 중 하나를 반환합니다.

## 핵심 방향

- Phase 1은 자동 실행이 아니라 `confirm` 중심의 파일럿입니다.
- 초기 범위는 20~30개 핵심 intent로 제한합니다.
- LLM은 후보 intent 선택과 slot JSON 작성만 담당합니다.
- 최종 decision은 스키마 검증과 정책 엔진이 결정합니다.
- Reranker, `/admin/reload`, fine-tuning은 MVP에서 제외합니다.

## 문서

- [PRD](docs/PRD.md): 제품 요구사항과 안전 정책
- [구현 계획](docs/PLAN_CODING.md): MVP 구조, 모듈 책임, 작업 목록
- [작업 원칙](AGENTS.md): 단순성, 가독성, 최소 변경 원칙

HTML 문서는 `docs/html/` 아래에 있습니다.

## 현재 상태

현재 저장소는 기획 및 구현 계획 문서 단계입니다. 실제 API, Docker 구성, 테스트 코드는 아직 생성되지 않았습니다.

## MVP 구성

```text
STT 텍스트
  -> 정규화 / 장비명 해석
  -> Qwen3-Embedding-0.6B 임베딩
  -> FAISS Top-K 검색
  -> 외부 LLM 후보 선택 + slot 추출
  -> 스키마 검증 / 정책 결정
  -> JSON 응답
```

## 주요 응답 decision

- `execute`: Phase 2 이후 검증된 non-risky high confidence 명령만 허용
- `confirm`: Phase 1 모든 제어 명령, risky 명령, medium confidence
- `reject`: OOD, low confidence, 스키마 실패, 필수 slot 누락

