#!/usr/bin/env python3
"""
QA Sync 인증 관리자
- 쿠키 저장/로드
- 브라우저 프로필 관리
- 로그인 플로우 지원
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# 인증 데이터 저장 경로
AUTH_DIR = Path.home() / ".qa-sync" / "auth"


def get_auth_path(site_name: str) -> Path:
    """사이트별 인증 데이터 경로"""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    return AUTH_DIR / f"{site_name}.json"


def save_cookies(site_name: str, cookies: List[Dict]) -> Path:
    """쿠키 저장"""
    auth_path = get_auth_path(site_name)

    data = {
        "site_name": site_name,
        "saved_at": datetime.now().isoformat(),
        "cookies": cookies
    }

    with open(auth_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 쿠키 저장됨: {auth_path}")
    return auth_path


def load_cookies(site_name: str) -> Optional[List[Dict]]:
    """쿠키 로드"""
    auth_path = get_auth_path(site_name)

    if not auth_path.exists():
        return None

    try:
        with open(auth_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cookies", [])
    except Exception as e:
        print(f"⚠️ 쿠키 로드 실패: {e}")
        return None


def delete_cookies(site_name: str) -> bool:
    """쿠키 삭제"""
    auth_path = get_auth_path(site_name)

    if auth_path.exists():
        auth_path.unlink()
        print(f"✅ 쿠키 삭제됨: {site_name}")
        return True
    return False


def list_saved_auth() -> List[str]:
    """저장된 인증 목록"""
    if not AUTH_DIR.exists():
        return []

    return [f.stem for f in AUTH_DIR.glob("*.json")]


def export_cookies_from_browser(url: str, site_name: str) -> Optional[Path]:
    """
    브라우저를 열어 수동 로그인 후 쿠키 저장

    1. 브라우저 창이 열림
    2. 사용자가 직접 로그인
    3. 로그인 완료 후 Enter 입력
    4. 쿠키 자동 저장
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright가 설치되지 않았습니다.")
        print("   python3 src/install.py 실행")
        return None

    print(f"\n🌐 브라우저를 열고 있습니다...")
    print(f"   URL: {url}")

    # Playwright 시작
    p = sync_playwright().start()

    # 브라우저 열기 (headless=False로 GUI 표시)
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # URL로 이동
    print(f"   페이지 로딩 중...")
    try:
        page.goto(url, wait_until="load", timeout=60000)
        print(f"   ✅ 페이지 로드 완료")
    except Exception as e:
        print(f"   ⚠️ 페이지 로드 경고 (브라우저는 유지): {e}")

    print(f"\n" + "="*50)
    print(f"   브라우저에서 로그인을 완료하세요.")
    print(f"   완료 후 이 터미널에서 Enter를 눌러주세요.")
    print(f"="*50 + "\n")

    # 사용자 입력 대기 (별도 처리)
    try:
        input("✋ Enter를 눌러 쿠키 저장... ")
    except EOFError:
        print("❌ 대화형 터미널이 필요합니다.")
        print("   직접 터미널에서 실행해주세요.")
        browser.close()
        p.stop()
        return None
    except KeyboardInterrupt:
        print("\n취소됨")
        browser.close()
        p.stop()
        return None

    # 쿠키 추출
    cookies = context.cookies()

    # 저장
    auth_path = save_cookies(site_name, cookies)

    # 정리
    browser.close()
    p.stop()

    print(f"\n✅ {len(cookies)}개 쿠키 저장 완료!")
    return auth_path


async def apply_cookies_async(context: BrowserContext, site_name: str) -> bool:
    """비동기 컨텍스트에 쿠키 적용"""
    cookies = load_cookies(site_name)

    if not cookies:
        return False

    try:
        await context.add_cookies(cookies)
        return True
    except Exception as e:
        print(f"⚠️ 쿠키 적용 실패: {e}")
        return False


def apply_cookies_sync(context, site_name: str) -> bool:
    """동기 컨텍스트에 쿠키 적용"""
    cookies = load_cookies(site_name)

    if not cookies:
        return False

    try:
        context.add_cookies(cookies)
        return True
    except Exception as e:
        print(f"⚠️ 쿠키 적용 실패: {e}")
        return False


def get_chrome_user_data_dir() -> Optional[Path]:
    """Chrome 기본 프로필 경로"""
    import platform

    system = platform.system()

    if system == "Darwin":  # macOS
        path = Path.home() / "Library/Application Support/Google/Chrome"
    elif system == "Windows":
        path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data"
    elif system == "Linux":
        path = Path.home() / ".config/google-chrome"
    else:
        return None

    return path if path.exists() else None


def use_chrome_profile(profile_name: str = "Default") -> Optional[Dict]:
    """
    기존 Chrome 프로필 사용 설정 반환

    주의: Chrome이 실행 중이면 사용 불가
    """
    user_data_dir = get_chrome_user_data_dir()

    if not user_data_dir:
        print("❌ Chrome 프로필을 찾을 수 없습니다.")
        return None

    profile_path = user_data_dir / profile_name

    if not profile_path.exists():
        print(f"❌ 프로필 '{profile_name}'을 찾을 수 없습니다.")
        print(f"   경로: {profile_path}")
        return None

    print(f"✅ Chrome 프로필 발견: {profile_name}")
    print(f"   경로: {user_data_dir}")
    print(f"\n⚠️  주의: Chrome을 먼저 종료해야 합니다!")

    return {
        "user_data_dir": str(user_data_dir),
        "profile": profile_name
    }


def list_chrome_profiles() -> List[str]:
    """Chrome 프로필 목록"""
    user_data_dir = get_chrome_user_data_dir()

    if not user_data_dir:
        return []

    profiles = ["Default"]

    # Profile 1, Profile 2, ... 찾기
    for item in user_data_dir.iterdir():
        if item.is_dir() and item.name.startswith("Profile "):
            profiles.append(item.name)

    return profiles


# CLI 인터페이스
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: auth_manager.py <command> [args]")
        print("")
        print("Commands:")
        print("  login <url> <site_name>  - 브라우저 로그인 후 쿠키 저장")
        print("  list                     - 저장된 인증 목록")
        print("  delete <site_name>       - 저장된 인증 삭제")
        print("  profiles                 - Chrome 프로필 목록")
        print("")
        print("Examples:")
        print("  python3 auth_manager.py login https://valley.town valley")
        print("  python3 auth_manager.py list")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "login" and len(sys.argv) > 3:
        url = sys.argv[2]
        site_name = sys.argv[3]
        export_cookies_from_browser(url, site_name)

    elif cmd == "list":
        sites = list_saved_auth()
        if sites:
            print("저장된 인증:")
            for site in sites:
                auth_path = get_auth_path(site)
                with open(auth_path) as f:
                    data = json.load(f)
                    saved_at = data.get("saved_at", "")[:19]
                    cookie_count = len(data.get("cookies", []))
                print(f"  - {site} ({cookie_count}개 쿠키, {saved_at})")
        else:
            print("저장된 인증 없음")

    elif cmd == "delete" and len(sys.argv) > 2:
        site_name = sys.argv[2]
        delete_cookies(site_name)

    elif cmd == "profiles":
        profiles = list_chrome_profiles()
        if profiles:
            print("Chrome 프로필:")
            for p in profiles:
                print(f"  - {p}")
        else:
            print("Chrome 프로필을 찾을 수 없습니다.")

    else:
        print(f"Unknown command: {cmd}")
