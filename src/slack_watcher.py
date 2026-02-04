#!/usr/bin/env python3
"""
QA Sync Slack Watcher
- Slack 채널/쓰레드 실시간 모니터링
- 새 메시지 감지 시 알림 또는 자동 처리
- Claude Code MCP와 연동하여 Linear 이슈 생성
"""

import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# 상태 관리자 임포트
sys.path.insert(0, str(Path(__file__).parent))
from state_manager import (
    load_state, get_project, is_message_synced,
    mark_message_synced, list_projects
)


class SlackWatcher:
    """Slack 채널 모니터링"""

    def __init__(self, project_name: str, poll_interval: int = 30):
        """
        Args:
            project_name: 모니터링할 프로젝트 이름
            poll_interval: 폴링 간격 (초)
        """
        self.project_name = project_name
        self.poll_interval = poll_interval
        self.project = get_project(project_name)

        if not self.project:
            raise ValueError(f"Project '{project_name}' not found. Run /qa-sync setup first.")

        self.channel = self.project["config"].get("slack_channel")
        self.thread_ts = self.project["config"].get("slack_thread_ts")

        if not self.channel:
            raise ValueError("Slack channel not configured for this project")

    def get_new_messages(self) -> list:
        """새 메시지 가져오기 (MCP 또는 API 사용)"""
        # 방법 1: Claude Code 호출로 MCP 사용
        # 방법 2: Slack API 직접 호출

        # 여기서는 마지막 확인 시간 이후 메시지를 필터링
        # 실제 구현에서는 Slack API 또는 MCP 결과를 파싱

        # Placeholder: 실제로는 MCP slack_read_channel 결과 사용
        return []

    def filter_unsynced(self, messages: list) -> list:
        """이미 처리된 메시지 필터링"""
        return [
            msg for msg in messages
            if not is_message_synced(self.project_name, msg.get("ts", ""))
        ]

    def analyze_message(self, message: dict) -> dict:
        """메시지 분석하여 이슈 타입 결정"""
        text = message.get("text", "").lower()

        # 키워드 기반 분류
        bug_keywords = ["안 됨", "에러", "깨짐", "오류", "버그", "안됨", "작동", "실패", "crash"]
        data_keywords = ["틀림", "안 맞", "중복", "잘못", "데이터", "값이", "표시"]
        improvement_keywords = ["좋겠", "개선", "추가", "제안", "하면", "있으면"]

        issue_type = "bug"  # default

        if any(kw in text for kw in improvement_keywords):
            issue_type = "improvement"
        elif any(kw in text for kw in data_keywords):
            issue_type = "data_error"
        elif any(kw in text for kw in bug_keywords):
            issue_type = "bug"

        # 제목 생성 (30자 이내)
        title = text[:30].strip()
        if len(text) > 30:
            title += "..."

        return {
            "type": issue_type,
            "title": title,
            "original_text": text,
            "user": message.get("user"),
            "ts": message.get("ts"),
            "attachments": message.get("files", [])
        }

    def create_linear_issue(self, analysis: dict) -> Optional[str]:
        """Linear 이슈 생성 (Claude Code MCP 사용)"""
        # 실제로는 Claude Code를 호출하거나 Linear API 직접 사용
        # 여기서는 placeholder

        issue_body = f"""## 보고자
{analysis.get('user', 'Unknown')}

## 증상
{analysis.get('original_text', '')}

## 원본 링크
Slack message ts: {analysis.get('ts', '')}
"""

        print(f"[Linear Issue] {analysis['type'].upper()}: {analysis['title']}")
        print(issue_body)

        # Placeholder: 실제 issue_id 반환
        return f"ISSUE-{int(time.time())}"

    def process_message(self, message: dict) -> bool:
        """메시지 처리 (분석 → 이슈 생성 → 상태 저장)"""
        try:
            analysis = self.analyze_message(message)
            issue_id = self.create_linear_issue(analysis)

            if issue_id:
                mark_message_synced(
                    self.project_name,
                    message.get("ts", ""),
                    issue_id,
                    analysis["type"]
                )
                return True
        except Exception as e:
            print(f"Error processing message: {e}")

        return False

    def watch(self, callback: Optional[Callable] = None, max_iterations: Optional[int] = None):
        """
        메시지 감시 시작

        Args:
            callback: 새 메시지 감지 시 호출할 콜백
            max_iterations: 최대 반복 횟수 (None이면 무한)
        """
        print(f"🔍 Watching Slack channel for project: {self.project_name}")
        print(f"   Channel: {self.channel}")
        print(f"   Thread: {self.thread_ts or '(entire channel)'}")
        print(f"   Poll interval: {self.poll_interval}s")
        print("-" * 50)

        iteration = 0

        while max_iterations is None or iteration < max_iterations:
            try:
                messages = self.get_new_messages()
                unsynced = self.filter_unsynced(messages)

                if unsynced:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(unsynced)} new messages")

                    for msg in unsynced:
                        success = self.process_message(msg)
                        status = "✅" if success else "❌"
                        print(f"  {status} {msg.get('ts', '')}")

                    if callback:
                        callback(unsynced)

                time.sleep(self.poll_interval)
                iteration += 1

            except KeyboardInterrupt:
                print("\n\n👋 Watcher stopped")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.poll_interval)


def watch_project(project_name: str, interval: int = 30):
    """프로젝트 감시 시작"""
    watcher = SlackWatcher(project_name, poll_interval=interval)
    watcher.watch()


def notify_new_messages(messages: list):
    """macOS 알림 표시"""
    count = len(messages)
    msg = f"QA Sync: {count}개 새 메시지 감지됨"

    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{msg}" with title "QA Sync"'
        ], capture_output=True)
    except Exception:
        pass


# CLI 인터페이스
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: slack_watcher.py <command> [args]")
        print("")
        print("Commands:")
        print("  watch <project_name> [interval]  - Start watching (default: 30s)")
        print("  list                             - List available projects")
        print("  status <project_name>            - Show project sync status")
        print("")
        print("Example:")
        print("  python3 slack_watcher.py watch valley-v2 60")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        projects = list_projects()
        if projects:
            print("Available projects:")
            for p in projects:
                proj = get_project(p)
                channel = proj["config"].get("slack_channel", "N/A") if proj else "N/A"
                print(f"  - {p} (channel: {channel})")
        else:
            print("No projects found. Run /qa-sync setup first.")

    elif cmd == "watch" and len(sys.argv) > 2:
        project_name = sys.argv[2]
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30

        try:
            watch_project(project_name, interval)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif cmd == "status" and len(sys.argv) > 2:
        project_name = sys.argv[2]
        project = get_project(project_name)

        if project:
            stats = project.get("stats", {})
            synced = len(project.get("synced_messages", []))

            print(f"Project: {project_name}")
            print(f"  Channel: {project['config'].get('slack_channel', 'N/A')}")
            print(f"  Messages synced: {synced}")
            print(f"  Issues created: {stats.get('total_issues', 0)}")
            print(f"    - Bugs: {stats.get('bugs', 0)}")
            print(f"    - Improvements: {stats.get('improvements', 0)}")
            print(f"    - Data errors: {stats.get('data_errors', 0)}")
        else:
            print(f"Project '{project_name}' not found")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
