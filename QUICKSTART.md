# 빠른 시작 — Cofa Probe에서 읽고 시작하기

`README.md`가 전체 안내이고, 이 문서는 **이미 공개된 `dogsa33/cofa-kit`을 과제 폴더에 가져오는 방법**만 정리합니다. 기존 과제 파일을 덮어쓰지 않습니다.

## A. Codex 연습과 시험

```powershell
# 과제 작업 폴더에서, 허용된 공개 저장소만 별도 폴더로 받는 예
git clone --depth 1 https://github.com/dogsa33/cofa-kit.git .cofa-kit
```

Codex 채팅 입력:

```text
.cofa-kit/prompts/SCENARIO.md를 읽어. 실제 과제 README의 필수조건과 제공 파일을 먼저 파악해 줘. 현업 확인 질문 목록(Q-ID·우선순위·근거·영향)을 먼저 보여줘. 현업 문의는 내가 직접 하고, 중요한 사용자 결정만 한 건씩 제안하고 내 답변을 기다려. 승인한 범위의 일반 구현과 검증은 스스로 진행하고, 웹 화면은 내가 한 시나리오씩 직접 확인할게.
```

수동 테스트만 시작하고 싶으면:

```text
.cofa-kit/prompts/UAT.md를 읽고 현재 구현의 UAT를 한 건씩 안내해 줘. 내가 실제 결과를 답하겠다.
```

**반드시 과제 안내가 허용한 작업/가져오기/Browser 방식을 따릅니다.** 시험 이후 AI 사용 금지 단계에는 이 요청을 하지 않습니다.

## B. Python 검사 (Windows)

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 examples/shuttle/verify_routes.py --data-dir examples/shuttle --routes examples/shuttle/routes_valid.json
python -X utf8 scripts/data_tools.py yield examples/semiconductor/yield_clean.csv
python -X utf8 scripts/data_tools.py spc examples/semiconductor/measurements.csv --baseline-count 25
python -X utf8 scripts/data_tools.py join examples/joins/inspections.csv examples/joins/defects.csv --left-key lot_id wafer_id --right-key lot_id wafer_id --relationship many_to_one
```

본 키트의 테스트 성공은 Cofa 실제 과제 성공의 증거가 아닙니다.
