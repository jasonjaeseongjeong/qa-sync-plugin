# QA Sync

Claude Code 플러그인 - PRD 기반 QA 시나리오 자동 생성 & Slack → Linear 이슈 동기화

## 이런 분들께 추천

- QA 시나리오를 매번 수동으로 작성하는 PM/QA
- Slack에 올라온 버그 리포트를 Linear로 옮기느라 시간 쓰는 개발자
- PRD 기반으로 체계적인 테스트 케이스를 만들고 싶은 팀

---

## 설치

### 방법 1: Marketplace에서 설치 (권장)

```bash
claude plugin marketplace add https://github.com/jasonjaeseongjeong/qa-sync-plugin
claude plugin install qa-sync@qa-sync-marketplace
```

### 방법 2: 전역 스킬로 설치

```bash
mkdir -p ~/.claude/skills/qa-sync
curl -o ~/.claude/skills/qa-sync/SKILL.md https://raw.githubusercontent.com/jasonjaeseongjeong/qa-sync-plugin/main/skills/qa-sync/SKILL.md
```

---

## 필요한 연동

| 서비스 | 용도 | 필수 |
|--------|------|------|
| Slack | QA 피드백 읽기 | O |
| Linear | 이슈 생성 | O |

> 연동이 안 되어 있으면 `/qa-sync` 실행 시 자동으로 안내합니다.

---

## 두 가지 모드

```
┌─────────────────────────────────────────────────────────────┐
│                        QA Sync                               │
├─────────────────────────────┬───────────────────────────────┤
│         Setup 모드           │          Sync 모드            │
│         /qa-sync             │     /qa-sync --mode sync      │
├─────────────────────────────┼───────────────────────────────┤
│  PRD + 사이트 분석           │  Slack 쓰레드 모니터링         │
│          ↓                   │           ↓                   │
│  QA 시나리오 자동 생성        │  메시지 → Linear 이슈 변환     │
├─────────────────────────────┼───────────────────────────────┤
│  QA 시작 전 1회 실행          │  QA 진행 중 반복 실행          │
└─────────────────────────────┴───────────────────────────────┘
```

---

## 사용법

### 1. Setup 모드: QA 시나리오 생성

```
/qa-sync
```

Claude가 순차적으로 물어봅니다:

1. **사이트 URL** - QA 대상 웹사이트
2. **PRD 파일** - 파일 경로 또는 '없음'
3. **Slack 채널/쓰레드** - QA 피드백 올릴 곳
4. **Linear 프로젝트** - 이슈 등록할 프로젝트

**결과물:** 마크다운 QA 시나리오 문서

### 2. Sync 모드: 이슈 동기화

```
/qa-sync --mode sync
```

Slack 쓰레드의 새 메시지를 분석해서:
- 버그/데이터 오류/개선 요청으로 분류
- 중복 이슈 체크
- Linear 이슈 자동 생성

---

## 생성되는 QA 시나리오 예시

| 유형 | 시나리오 | 확인 사항 | ☐ |
|------|---------|----------|---|
| Happy | 1. 로그인 2. 대시보드 클릭 | 대시보드가 로드되는지 | |
| Edge | 1. 100자 이상 제목 입력 | 말줄임 처리되는지 | |
| Error | 1. 네트워크 끊기 2. 저장 클릭 | 에러 토스트가 뜨는지 | |
| Boundary | 1. 0개 아이템 상태에서 접속 | 빈 상태 UI가 표시되는지 | |

### 시나리오 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| Happy | 정상 흐름 | 카드 클릭 → 상세 열림 |
| Alternative | 다른 경로 | 키보드로 상세 열기 |
| Edge | 경계 상황 | 첫 번째/마지막 카드 |
| Error | 오류 상황 | 네트워크 끊김 |
| Boundary | 경계값 | 최대 길이, 0개/100개 |

---

## Linear 이슈 생성 형식

Slack 메시지가 이렇게 변환됩니다:

```markdown
## 보고자
김철수 (@kim.cs)

## 증상
결제 버튼 클릭 시 무한 로딩

## 스크린샷
[첨부 이미지]

## 원문
> 결제 버튼 눌렀는데 계속 로딩만 돼요 ㅠㅠ

## 원본 링크
[Slack에서 보기](https://...)
```

---

## 트러블슈팅

### 스킬이 안 보여요

```bash
# 설치 확인
claude plugin list

# 재설치
claude plugin uninstall qa-sync@qa-sync-marketplace
claude plugin install qa-sync@qa-sync-marketplace
```

### Slack/Linear 연동 오류

`/qa-sync` 실행 시 자동으로 연동 가이드가 나옵니다.

---

## 라이선스

MIT

---

## 만든 사람

[NeurofusionAI](https://github.com/jasonjaeseongjeong)
