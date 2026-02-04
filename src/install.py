#!/usr/bin/env python3
"""
QA Sync 설치 스크립트
- Python venv 생성
- 필요한 패키지 설치
- Playwright 브라우저 설치
"""

import os
import subprocess
import sys
from pathlib import Path


# 설치 경로
QA_SYNC_HOME = Path.home() / ".qa-sync"
VENV_PATH = QA_SYNC_HOME / "venv"
REQUIREMENTS = ["playwright>=1.40.0"]


def print_step(msg: str):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}\n")


def check_python():
    """Python 버전 확인"""
    version = sys.version_info
    if version < (3, 8):
        print(f"❌ Python 3.8 이상 필요 (현재: {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def create_venv():
    """가상환경 생성"""
    print_step("1. 가상환경 생성")

    if VENV_PATH.exists():
        print(f"⚠️  기존 venv 발견: {VENV_PATH}")
        response = input("삭제하고 새로 생성할까요? (y/N): ").strip().lower()
        if response == 'y':
            import shutil
            shutil.rmtree(VENV_PATH)
        else:
            print("기존 venv 사용")
            return True

    try:
        subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)
        print(f"✅ venv 생성 완료: {VENV_PATH}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ venv 생성 실패: {e}")
        return False


def get_pip():
    """venv의 pip 경로"""
    if sys.platform == "win32":
        return VENV_PATH / "Scripts" / "pip"
    return VENV_PATH / "bin" / "pip"


def get_python():
    """venv의 python 경로"""
    if sys.platform == "win32":
        return VENV_PATH / "Scripts" / "python"
    return VENV_PATH / "bin" / "python"


def install_packages():
    """패키지 설치"""
    print_step("2. 패키지 설치")

    pip = get_pip()

    # pip 업그레이드
    try:
        subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True, capture_output=True)
    except:
        pass

    # 패키지 설치
    for package in REQUIREMENTS:
        print(f"📦 Installing {package}...")
        try:
            subprocess.run([str(pip), "install", package], check=True)
            print(f"✅ {package} 설치 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} 설치 실패: {e}")
            return False

    return True


def install_playwright_browsers():
    """Playwright 브라우저 설치"""
    print_step("3. Playwright 브라우저 설치")

    python = get_python()

    try:
        subprocess.run([str(python), "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Chromium 브라우저 설치 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 브라우저 설치 실패: {e}")
        return False


def create_wrapper_script():
    """실행 래퍼 스크립트 생성"""
    print_step("4. 실행 스크립트 생성")

    python = get_python()
    scripts_dir = QA_SYNC_HOME / "bin"
    scripts_dir.mkdir(exist_ok=True)

    # qa-crawl 스크립트
    crawl_script = scripts_dir / "qa-crawl"
    crawl_content = f"""#!/bin/bash
"{python}" "{Path(__file__).parent / 'site_crawler.py'}" "$@"
"""
    crawl_script.write_text(crawl_content)
    crawl_script.chmod(0o755)

    # qa-dashboard 스크립트
    dashboard_script = scripts_dir / "qa-dashboard"
    dashboard_content = f"""#!/bin/bash
"{python}" "{Path(__file__).parent / 'notion_dashboard.py'}" "$@"
"""
    dashboard_script.write_text(dashboard_content)
    dashboard_script.chmod(0o755)

    # qa-watch 스크립트
    watch_script = scripts_dir / "qa-watch"
    watch_content = f"""#!/bin/bash
"{python}" "{Path(__file__).parent / 'slack_watcher.py'}" "$@"
"""
    watch_script.write_text(watch_content)
    watch_script.chmod(0o755)

    print(f"✅ 스크립트 생성 완료: {scripts_dir}")
    print(f"   - qa-crawl: 사이트 크롤링")
    print(f"   - qa-dashboard: 대시보드 생성")
    print(f"   - qa-watch: Slack 모니터링")

    return scripts_dir


def print_usage(scripts_dir: Path):
    """사용법 출력"""
    print_step("설치 완료!")

    print(f"""
사용법:

1. PATH에 추가 (선택):
   export PATH="{scripts_dir}:$PATH"

   또는 ~/.zshrc 또는 ~/.bashrc에 추가

2. 직접 실행:
   {scripts_dir}/qa-crawl https://example.com ./screenshots
   {scripts_dir}/qa-dashboard show project-name
   {scripts_dir}/qa-watch watch project-name

3. Claude Code에서:
   /qa-sync 실행 시 자동으로 크롤링 사용
""")


def check_installation():
    """설치 확인"""
    print_step("설치 확인")

    python = get_python()

    try:
        result = subprocess.run(
            [str(python), "-c", "from playwright.sync_api import sync_playwright; print('OK')"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and "OK" in result.stdout:
            print("✅ Playwright 정상 작동")
            return True
        else:
            print(f"❌ Playwright 오류: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 확인 실패: {e}")
        return False


def uninstall():
    """제거"""
    print_step("QA Sync 제거")

    if QA_SYNC_HOME.exists():
        response = input(f"정말 삭제할까요? {QA_SYNC_HOME} (y/N): ").strip().lower()
        if response == 'y':
            import shutil
            shutil.rmtree(QA_SYNC_HOME)
            print("✅ 삭제 완료")
        else:
            print("취소됨")
    else:
        print("설치된 항목 없음")


def main():
    print("""
╔═══════════════════════════════════════════════════╗
║           QA Sync 설치 스크립트                    ║
╚═══════════════════════════════════════════════════╝
""")

    # 명령어 처리
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "uninstall":
            uninstall()
            return
        elif cmd == "check":
            check_installation()
            return
        elif cmd == "help":
            print("Usage: install.py [command]")
            print("Commands:")
            print("  (none)     - 설치")
            print("  check      - 설치 확인")
            print("  uninstall  - 제거")
            return

    # 설치 시작
    QA_SYNC_HOME.mkdir(exist_ok=True)

    if not check_python():
        sys.exit(1)

    if not create_venv():
        sys.exit(1)

    if not install_packages():
        sys.exit(1)

    if not install_playwright_browsers():
        sys.exit(1)

    scripts_dir = create_wrapper_script()

    if not check_installation():
        print("\n⚠️  설치는 완료되었으나 확인 실패. 수동 확인 필요.")

    print_usage(scripts_dir)


if __name__ == "__main__":
    main()
