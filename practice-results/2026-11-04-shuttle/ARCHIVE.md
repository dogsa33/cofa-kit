# 통근버스 모의 과제 연습 결과 — 2026-11-04

사용자가 실행하고 검토한 연습 결과를 별도로 보관한 기록입니다. 실제 시험 제출물이나 공식 정답이 아닙니다. 문제의 원본 안내에 따라 데이터셋과 데모 계정은 합성 연습용입니다.

- 구현 코드: 루트의 CommonJS 파일과 public/
- 입력: datasets/의 기준·정상·오류 시나리오
- 기준 결과: artifacts/route_plan.json (기준 데이터 v1)
- 저장 시점 실행 결과: artifacts/current_route_plan.json (S1_shift_changed, 데이터 v2, 정책 v1)
- 저장 시점 지표·독립 검산: artifacts/archive_snapshot.json
- 기존 자동 테스트 기록: artifacts/test-results.txt (12 PASS, 0 FAIL; 보관 작업 중 전체 테스트를 다시 실행하지 않음)
- 최종 검토: FINAL_REVIEW.md
- 구현·검증 설명: IMPLEMENTATION_REPORT.md
- 실행 방법: README_RUN.md
- 실제 사용자 정책 선택: decision.json

## 다시 실행

Node.js 24 이상에서 이 폴더로 이동한 뒤 아래 명령을 실행합니다. 외부 패키지 설치는 필요 없습니다.

```text
node server.cjs
```

http://localhost:3000 에 접속합니다. 새 실행 DB는 기준 데이터 v1로 초기화됩니다. 저장 당시 적용된 S1_shift_changed 결과는 current_route_plan.json에서 확인할 수 있으며, UI에서 같은 스냅샷을 적용해 다시 계산할 수 있습니다. 상세 데모 계정과 테스트 명령은 README_RUN.md를 참고하세요.

SQLite 실행 DB와 로그인 세션·암호 해시는 보관하지 않았습니다. 공개 준비 키트의 중복 사본인 .cofa-kit도 제외했습니다. 원본 코드·입력·기존 보고서·기존 기준 산출물은 수정하지 않았습니다. 기존 보고서의 서버 실행 상태와 외부 전송 관련 문구는 연습 당시의 기록이며, 이 보관 작업은 그 이후 사용자의 요청으로 수행했습니다.

파일별 SHA-256은 ARCHIVE_MANIFEST.json에 있습니다. 저장 시각: 2026-11-04T07:55:53.234Z
