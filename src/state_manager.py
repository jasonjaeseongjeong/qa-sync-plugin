#!/usr/bin/env python3
"""
QA Sync State Manager
- QA 세션 상태 저장/로드
- 처리된 Slack 메시지 추적
- 시나리오 완료 상태 관리
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# 기본 저장 경로
DEFAULT_STATE_DIR = Path.home() / ".qa-sync"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "state.json"


def get_state_path(project_name: Optional[str] = None) -> Path:
    """프로젝트별 상태 파일 경로 반환"""
    if project_name:
        return DEFAULT_STATE_DIR / f"{project_name}.json"
    return DEFAULT_STATE_FILE


def init_state() -> dict:
    """빈 상태 초기화"""
    return {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "projects": {}
    }


def init_project(name: str) -> dict:
    """프로젝트 초기 상태"""
    return {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "config": {
            "site_url": None,
            "prd_path": None,
            "slack_channel": None,
            "slack_thread_ts": None,
            "linear_project_id": None,
            "linear_project_url": None
        },
        "scenarios": [],
        "synced_messages": [],  # 이미 처리한 Slack 메시지 ts
        "issues_created": [],   # 생성한 Linear 이슈 ID
        "stats": {
            "total_scenarios": 0,
            "completed_scenarios": 0,
            "total_issues": 0,
            "bugs": 0,
            "improvements": 0,
            "data_errors": 0
        }
    }


def load_state() -> dict:
    """상태 파일 로드"""
    DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)

    if DEFAULT_STATE_FILE.exists():
        with open(DEFAULT_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return init_state()


def save_state(state: dict) -> None:
    """상태 파일 저장"""
    DEFAULT_STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now().isoformat()

    with open(DEFAULT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_project(project_name: str) -> Optional[dict]:
    """프로젝트 상태 조회"""
    state = load_state()
    return state["projects"].get(project_name)


def create_project(project_name: str, config: dict) -> dict:
    """새 프로젝트 생성"""
    state = load_state()

    if project_name in state["projects"]:
        # 기존 프로젝트 업데이트
        state["projects"][project_name]["config"].update(config)
    else:
        # 새 프로젝트 생성
        project = init_project(project_name)
        project["config"].update(config)
        state["projects"][project_name] = project

    save_state(state)
    return state["projects"][project_name]


def update_project_config(project_name: str, config: dict) -> dict:
    """프로젝트 설정 업데이트"""
    state = load_state()

    if project_name not in state["projects"]:
        return create_project(project_name, config)

    state["projects"][project_name]["config"].update(config)
    save_state(state)
    return state["projects"][project_name]


def add_scenarios(project_name: str, scenarios: list) -> None:
    """시나리오 추가"""
    state = load_state()

    if project_name not in state["projects"]:
        state["projects"][project_name] = init_project(project_name)

    project = state["projects"][project_name]
    project["scenarios"].extend(scenarios)
    project["stats"]["total_scenarios"] = len(project["scenarios"])

    save_state(state)


def mark_scenario_completed(project_name: str, scenario_id: int) -> None:
    """시나리오 완료 표시"""
    state = load_state()

    if project_name in state["projects"]:
        project = state["projects"][project_name]
        if 0 <= scenario_id < len(project["scenarios"]):
            project["scenarios"][scenario_id]["completed"] = True
            project["scenarios"][scenario_id]["completed_at"] = datetime.now().isoformat()
            project["stats"]["completed_scenarios"] = sum(
                1 for s in project["scenarios"] if s.get("completed", False)
            )
            save_state(state)


def is_message_synced(project_name: str, message_ts: str) -> bool:
    """메시지가 이미 처리되었는지 확인"""
    state = load_state()

    if project_name in state["projects"]:
        return message_ts in state["projects"][project_name]["synced_messages"]
    return False


def mark_message_synced(project_name: str, message_ts: str, issue_id: str, issue_type: str) -> None:
    """메시지 처리 완료 표시"""
    state = load_state()

    if project_name not in state["projects"]:
        state["projects"][project_name] = init_project(project_name)

    project = state["projects"][project_name]

    if message_ts not in project["synced_messages"]:
        project["synced_messages"].append(message_ts)

    project["issues_created"].append({
        "issue_id": issue_id,
        "message_ts": message_ts,
        "issue_type": issue_type,
        "created_at": datetime.now().isoformat()
    })

    # 통계 업데이트
    project["stats"]["total_issues"] += 1
    if issue_type == "bug":
        project["stats"]["bugs"] += 1
    elif issue_type == "improvement":
        project["stats"]["improvements"] += 1
    elif issue_type == "data_error":
        project["stats"]["data_errors"] += 1

    save_state(state)


def get_project_stats(project_name: str) -> dict:
    """프로젝트 통계 조회"""
    state = load_state()

    if project_name in state["projects"]:
        return state["projects"][project_name]["stats"]
    return {}


def list_projects() -> list:
    """모든 프로젝트 목록"""
    state = load_state()
    return list(state["projects"].keys())


def get_unsynced_count(project_name: str, all_message_ts: list) -> int:
    """아직 처리 안 된 메시지 수"""
    state = load_state()

    if project_name in state["projects"]:
        synced = set(state["projects"][project_name]["synced_messages"])
        return len([ts for ts in all_message_ts if ts not in synced])
    return len(all_message_ts)


# CLI 인터페이스
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: state_manager.py <command> [args]")
        print("Commands: list, get <project>, stats <project>, init <project>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        projects = list_projects()
        if projects:
            print("Projects:")
            for p in projects:
                print(f"  - {p}")
        else:
            print("No projects found.")

    elif cmd == "get" and len(sys.argv) > 2:
        project = get_project(sys.argv[2])
        if project:
            print(json.dumps(project, ensure_ascii=False, indent=2))
        else:
            print(f"Project '{sys.argv[2]}' not found.")

    elif cmd == "stats" and len(sys.argv) > 2:
        stats = get_project_stats(sys.argv[2])
        if stats:
            print(f"Stats for '{sys.argv[2]}':")
            print(f"  Scenarios: {stats.get('completed_scenarios', 0)}/{stats.get('total_scenarios', 0)}")
            print(f"  Issues: {stats.get('total_issues', 0)}")
            print(f"    - Bugs: {stats.get('bugs', 0)}")
            print(f"    - Improvements: {stats.get('improvements', 0)}")
            print(f"    - Data errors: {stats.get('data_errors', 0)}")
        else:
            print(f"No stats for '{sys.argv[2]}'.")

    elif cmd == "init" and len(sys.argv) > 2:
        project = create_project(sys.argv[2], {})
        print(f"Project '{sys.argv[2]}' initialized.")

    else:
        print(f"Unknown command: {cmd}")
