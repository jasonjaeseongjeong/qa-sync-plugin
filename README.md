# QA Sync

PRD + 사이트 분석으로 QA 시나리오 자동 생성하고, Slack 피드백을 Linear 이슈로 동기화합니다.

## 설치

```bash
claude plugin add https://github.com/neurofusion/qa-sync-plugin
```

## 필요한 연동

- **Slack** - QA 피드백 쓰레드 읽기
- **Linear** - 이슈 생성

## 사용법

### 1. 초기 세팅

```
/qa-sync
```

Claude가 물어봅니다:
1. QA 대상 사이트 URL
2. PRD 파일 (첨부 또는 URL)
3. Slack 쓰레드 URL
4. Linear 프로젝트 URL

→ PRD와 사이트를 분석해서 **QA 시나리오 문서**를 자동 생성합니다.

### 2. 이슈 동기화

```
/qa-sync --mode sync
```

→ Slack 쓰레드의 새 메시지를 분석해서 Linear 이슈로 등록합니다.

## 생성되는 QA 시나리오 형식

| 유형 | 시나리오 | 확인 사항 | ☐ |
|-----|---------|----------|---|
| Happy | 1. 로그인 2. 메뉴 클릭 | 화면이 로드되는지 확인 | |
| Edge | 1. 긴 제목 입력 | 말줄임 처리되는지 확인 | |
| Error | 1. 네트워크 끊기 2. 접속 | 에러 메시지 표시되는지 확인 | |

## 시나리오 유형

| 유형 | 설명 |
|-----|------|
| Happy | 정상 흐름 |
| Alternative | 다른 경로 |
| Edge | 경계 상황 |
| Error | 오류 상황 |
| Boundary | 경계값 테스트 |

## 라이선스

MIT
