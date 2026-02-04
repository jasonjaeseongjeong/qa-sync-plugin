---
description: PRD + 사이트 분석으로 QA 시나리오 자동 생성, Slack → Linear 이슈 동기화
---

# QA Sync

PRD + 사이트 분석으로 QA 시나리오 자동 생성, Slack 피드백을 Linear 이슈로 동기화.

## 상태 관리

**중요: 모든 작업 전 상태 파일 확인 필수**

```bash
# 프로젝트 목록 확인
python3 ~/.claude/skills/qa-sync/src/state_manager.py list

# 프로젝트 상태 확인
python3 ~/.claude/skills/qa-sync/src/state_manager.py get <project_name>

# 통계 확인
python3 ~/.claude/skills/qa-sync/src/state_manager.py stats <project_name>
```

상태 파일 위치: `~/.qa-sync/state.json`

## 트리거

- "QA 시나리오 만들어줘"
- "QA 세팅"
- "Slack 이슈 동기화"
- `/qa-sync`

---

## 모드 1: Setup (초기 세팅)

### Step 0. 기존 프로젝트 확인

```bash
python3 ~/.claude/skills/qa-sync/src/state_manager.py list
```

기존 프로젝트가 있으면:
> "기존 프로젝트 [프로젝트명]이 있습니다. 이어서 진행할까요, 새로 시작할까요?"

### Step 1. 연동 확인

1. Slack 연동 체크 → 없으면 `suggest_connectors` 호출
2. Linear 연동 체크 → 없으면 `suggest_connectors` 호출

### Step 2. 정보 수집 (순차적으로 하나씩)

**중요: 질문은 반드시 하나씩 순차적으로 진행. 이전 답변을 받은 후 다음 질문.**

1. 먼저 물어봄:
   > "프로젝트 이름을 정해주세요. (예: valley-v2, checkout-redesign)"

2. 답변 받은 후:
   > "QA 대상 사이트 URL을 알려주세요."

3. 답변 받은 후:
   > "PRD 파일이 있나요? (파일 경로 또는 '없음' 입력)"

4. 답변 받은 후:
   > "QA 피드백을 남길 Slack 채널 또는 쓰레드 URL을 알려주세요."

5. 답변 받은 후:
   > "이슈를 등록할 Linear 프로젝트 URL을 알려주세요."

**참고:** 사용자가 이미 제공한 정보는 다시 묻지 않음.

### Step 2.5. 상태 저장

수집한 정보를 상태 파일에 저장:
```python
# Python으로 상태 저장
import sys
sys.path.insert(0, str(Path.home() / ".claude/skills/qa-sync/src"))
from state_manager import create_project

create_project("프로젝트명", {
    "site_url": "...",
    "prd_path": "...",
    "slack_channel": "...",
    "linear_project_url": "..."
})
```

### Step 3. QA 시나리오 자동 생성

**PRD 분석:**
- 주요 기능 추출
- 유저 플로우 파악
- 엣지 케이스 식별

**사이트 자동 크롤링:**
```bash
# Playwright로 사이트 UI 요소 자동 추출
python3 ~/.claude/skills/qa-sync/src/site_crawler.py <site_url> ./qa-screenshots
```

**로그인 페이지 감지 시 (중요):**

크롤링 결과에서 로그인 폼이 감지되면 (email/password 필드, 로그인 버튼 등):

1. 사용자에게 안내:
   > "로그인이 필요한 페이지입니다. 브라우저에서 로그인을 진행해주세요."

2. 로그인 실행:
   ```bash
   python3 ~/.claude/skills/qa-sync/src/auth_manager.py login <site_url> <project_name>
   ```
   - 브라우저가 열림
   - 사용자가 직접 로그인
   - 터미널에서 Enter 입력
   - 쿠키 자동 저장

3. 로그인 완료 후 인증된 상태로 다시 크롤링:
   ```bash
   python3 ~/.claude/skills/qa-sync/src/site_crawler.py --auth <project_name> <site_url> ./qa-screenshots
   ```

4. **로그인 실패 또는 취소 시** 사용자에게 질문:
   > "로그인에 실패했습니다. 어떻게 진행할까요?"
   > 1. 다시 로그인 시도
   > 2. PRD 기반으로만 시나리오 생성 (사이트 분석 없이)

**참고:** 크롤링 완료 후 인증 쿠키는 자동 삭제됩니다.

크롤링 결과:
- 버튼 목록 (텍스트, 선택자, 활성화 상태)
- 폼 구조 (필드명, 타입, 필수 여부)
- 네비게이션 메뉴
- 인터랙티브 요소 (드롭다운, 탭, 토글, 슬라이더)
- 내부/외부 링크 목록
- 스크린샷 (전체 페이지 + 뷰포트)

**분석 결과 활용:**
크롤링 결과를 기반으로 시나리오 생성:
- 각 버튼 클릭 시나리오
- 폼 입력/제출 시나리오
- 네비게이션 흐름 시나리오
- 에지 케이스 (빈 입력, 긴 텍스트 등)

### Step 4. QA 가이드 생성

마크다운 파일로 저장.

### Step 5. 확인

> "QA 가이드가 생성되었습니다. 검토 후 수정할 부분 있으면 알려주세요."

---

## 모드 2: Sync (이슈 동기화)

### Step 0. 프로젝트 상태 로드

```bash
python3 ~/.claude/skills/qa-sync/src/state_manager.py list
```

프로젝트 선택 후 설정 로드:
```bash
python3 ~/.claude/skills/qa-sync/src/state_manager.py get <project_name>
```

→ 저장된 Slack 채널, Linear 프로젝트 정보 사용

### Step 1. Slack 쓰레드 읽기

`slack_read_thread`로 새 메시지 확인.

### Step 2. 이미 처리된 메시지 필터링

상태 파일의 `synced_messages`와 비교하여 새 메시지만 처리:
```python
from state_manager import is_message_synced

# 각 메시지에 대해
if is_message_synced("프로젝트명", message_ts):
    continue  # 이미 처리됨, 스킵
```

### Step 3. 메시지 분석

**이슈 유형:**
- 🐛 버그 (bug): 안 됨, 에러, 깨짐
- 📊 데이터 (data_error): 틀림, 안 맞음, 중복
- 💡 개선 (improvement): ~하면 좋겠다

**제목 생성:**
- 메시지 핵심을 30자 이내로 요약

### Step 4. 중복 체크

Linear 프로젝트에서 유사 이슈 검색.
- 있으면 → 기존 이슈에 코멘트
- 없으면 → 새 이슈 생성

### Step 5. Linear 이슈 생성

```markdown
## 보고자
{작성자} (@{Slack ID})

## 증상
{정리한 증상 설명}

## 스크린샷
{첨부된 이미지}

## 원문
> {원본 Slack 메시지}

## 원본 링크
[Slack에서 보기]({메시지 링크})
```

### Step 6. 상태 업데이트

이슈 생성 후 상태 파일에 기록:
```python
from state_manager import mark_message_synced

mark_message_synced("프로젝트명", message_ts, issue_id, "bug")  # or "improvement", "data_error"
```

### Step 7. 완료 알림

통계와 함께 보고:
```bash
python3 ~/.claude/skills/qa-sync/src/state_manager.py stats <project_name>
```

> "N개 메시지 처리 완료. 새 이슈 X개, 기존 이슈 코멘트 Y개."
> "전체 현황: 버그 X개, 개선 Y개, 데이터 오류 Z개"

---

## 모드 3: Watch (실시간 감지)

백그라운드에서 Slack 채널을 모니터링하고 새 메시지 감지 시 자동으로 Linear 이슈 생성.

### 사용법

```bash
# 프로젝트 목록 확인
python3 ~/.claude/skills/qa-sync/src/slack_watcher.py list

# 감시 시작 (30초 간격)
python3 ~/.claude/skills/qa-sync/src/slack_watcher.py watch <project_name>

# 감시 시작 (60초 간격)
python3 ~/.claude/skills/qa-sync/src/slack_watcher.py watch <project_name> 60

# 동기화 상태 확인
python3 ~/.claude/skills/qa-sync/src/slack_watcher.py status <project_name>
```

### 백그라운드 실행

```bash
# 백그라운드에서 실행
nohup python3 ~/.claude/skills/qa-sync/src/slack_watcher.py watch <project_name> > ~/qa-sync.log 2>&1 &

# 로그 확인
tail -f ~/qa-sync.log

# 중지
pkill -f slack_watcher.py
```

---

## 시나리오 생성 가이드

### 시나리오 유형

| 유형 | 설명 | 예시 |
|-----|------|-----|
| Happy | 정상 흐름 | 카드 클릭 → 상세 열림 |
| Alternative | 다른 경로 | 키보드로 상세 열기 |
| Edge | 경계 상황 | 첫 번째/마지막 카드 |
| Error | 오류 상황 | 네트워크 끊김 |
| Boundary | 경계값 | 최대 길이, 0개/100개 |

### 시나리오 테이블 형식

| 유형 | 시나리오 | 확인 사항 | ☐ |
|-----|---------|----------|---|

- **시나리오**: 단계별로 (1. xxx 2. xxx)
- **확인 사항**: "~하는지 확인"

### AI/데이터 서비스 판단

PRD에 아래 키워드가 있으면 추가 테스트:

| 키워드 | 추가 테스트 |
|-------|-----------|
| AI, ML, 추천, 예측 | 환각 체크, 일관성 |
| 실시간, 라이브 | 시간 정확성, 지연 |
| 요약, 분석 | 출처 대조, 정확성 |

### 공통 에지 케이스

| 상황 | 확인 사항 |
|-----|----------|
| 빈 상태 | 데이터 없을 때 UI |
| 로딩 실패 | 이미지/API 에러 |
| 극단 데이터 | 긴 텍스트, 특수문자 |
| 경계값 | 최소/최대 개수 |

### 좋은 시나리오 원칙

- 1 시나리오 = 1 검증
- 독립 실행 (의존성 없음)
- 3-5 스텝 이내

---

## 모드 4: Dashboard (Notion 대시보드)

QA 진행 현황을 Notion 페이지로 자동 생성/업데이트.

### 사용법

```bash
# 대시보드 출력 (콘솔)
python3 ~/.claude/skills/qa-sync/src/notion_dashboard.py show <project_name>

# 전체 프로젝트 요약
python3 ~/.claude/skills/qa-sync/src/notion_dashboard.py show

# 마크다운 파일로 내보내기
python3 ~/.claude/skills/qa-sync/src/notion_dashboard.py export ./dashboard.md <project_name>

# Notion 업데이트 안내
python3 ~/.claude/skills/qa-sync/src/notion_dashboard.py notion <project_name>
```

### Notion 업데이트

대시보드 콘텐츠를 Notion에 업데이트하려면:

1. 대시보드 마크다운 생성:
   ```bash
   python3 ~/.claude/skills/qa-sync/src/notion_dashboard.py show <project_name>
   ```

2. Claude Code에서 Notion MCP 사용:
   ```
   mcp__notion__notion-update-page 또는
   mcp__notion__notion-create-pages
   ```

### 대시보드 내용

- 📊 프로젝트 요약 (사이트, Slack, Linear 링크)
- 🏃 시나리오 진행률 (프로그레스 바)
- 🐛 이슈 현황 (버그/개선/데이터 비율)
- 📋 최근 이슈 목록
- 📝 시나리오 목록 (미완료/완료)
