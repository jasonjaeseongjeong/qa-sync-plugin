#!/usr/bin/env python3
"""
QA Sync 테스트 자동화 실행기
- QA 시나리오를 자동으로 실행
- 결과 리포트 생성
- 스크린샷 캡처
"""

import asyncio
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 인증 모듈
try:
    from auth_manager import load_cookies
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestStep:
    """테스트 단계"""
    action: str  # click, fill, navigate, wait, assert
    target: Optional[str] = None  # selector or URL
    value: Optional[str] = None  # input value or expected text
    description: str = ""


@dataclass
class TestCase:
    """테스트 케이스"""
    id: str
    name: str
    category: str  # happy, edge, error, boundary
    steps: List[TestStep] = field(default_factory=list)
    expected: str = ""
    priority: str = "medium"  # high, medium, low


@dataclass
class TestResult:
    """테스트 결과"""
    test_id: str
    test_name: str
    status: TestStatus
    duration_ms: int = 0
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    steps_completed: int = 0
    total_steps: int = 0


@dataclass
class TestReport:
    """테스트 리포트"""
    project_name: str
    site_url: str
    run_at: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: int = 0
    duration_ms: int = 0
    results: List[TestResult] = field(default_factory=list)


class TestRunner:
    """QA 테스트 자동 실행기"""

    def __init__(self, headless: bool = True, auth_site: Optional[str] = None):
        self.headless = headless
        self.auth_site = auth_site
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """브라우저 시작"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright가 설치되지 않았습니다. python3 src/install.py 실행")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720}
        )

        # 인증 쿠키 적용
        if self.auth_site and AUTH_AVAILABLE:
            cookies = load_cookies(self.auth_site)
            if cookies:
                await self.context.add_cookies(cookies)
                print(f"✅ 인증 쿠키 적용: {self.auth_site}")

        self.page = await self.context.new_page()

    async def stop(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def run_step(self, step: TestStep) -> bool:
        """단일 스텝 실행"""
        try:
            if step.action == "navigate":
                await self.page.goto(step.target, wait_until="load", timeout=30000)
                await self.page.wait_for_timeout(1000)

            elif step.action == "click":
                await self.page.click(step.target, timeout=10000)
                await self.page.wait_for_timeout(500)

            elif step.action == "fill":
                await self.page.fill(step.target, step.value or "")

            elif step.action == "select":
                await self.page.select_option(step.target, step.value)

            elif step.action == "check":
                await self.page.check(step.target)

            elif step.action == "uncheck":
                await self.page.uncheck(step.target)

            elif step.action == "hover":
                await self.page.hover(step.target)
                await self.page.wait_for_timeout(300)

            elif step.action == "press":
                await self.page.press(step.target or "body", step.value or "Enter")

            elif step.action == "wait":
                timeout = int(step.value) if step.value else 1000
                await self.page.wait_for_timeout(timeout)

            elif step.action == "wait_for":
                await self.page.wait_for_selector(step.target, timeout=10000)

            elif step.action == "assert_visible":
                element = await self.page.query_selector(step.target)
                if not element:
                    return False
                is_visible = await element.is_visible()
                return is_visible

            elif step.action == "assert_text":
                element = await self.page.query_selector(step.target)
                if not element:
                    return False
                text = await element.inner_text()
                return step.value in text if step.value else bool(text)

            elif step.action == "assert_url":
                current_url = self.page.url
                return step.value in current_url if step.value else True

            elif step.action == "assert_not_visible":
                element = await self.page.query_selector(step.target)
                if not element:
                    return True
                is_visible = await element.is_visible()
                return not is_visible

            elif step.action == "screenshot":
                await self.page.screenshot(path=step.target or "screenshot.png")

            else:
                print(f"⚠️ 알 수 없는 액션: {step.action}")
                return True

            return True

        except Exception as e:
            print(f"❌ 스텝 실패 [{step.action}]: {e}")
            return False

    async def run_test(self, test: TestCase, screenshot_dir: str) -> TestResult:
        """단일 테스트 케이스 실행"""
        start_time = datetime.now()
        steps_completed = 0
        error_message = None
        screenshot_path = None

        try:
            for i, step in enumerate(test.steps):
                print(f"  [{i+1}/{len(test.steps)}] {step.action}: {step.description or step.target}")

                success = await self.run_step(step)

                if not success:
                    error_message = f"Step {i+1} 실패: {step.action} - {step.target}"
                    # 실패 시 스크린샷
                    screenshot_path = f"{screenshot_dir}/{test.id}_failed.png"
                    await self.page.screenshot(path=screenshot_path)
                    break

                steps_completed += 1

            status = TestStatus.PASSED if steps_completed == len(test.steps) else TestStatus.FAILED

            # 성공 시에도 스크린샷 (선택적)
            if status == TestStatus.PASSED:
                screenshot_path = f"{screenshot_dir}/{test.id}_passed.png"
                await self.page.screenshot(path=screenshot_path)

        except Exception as e:
            status = TestStatus.ERROR
            error_message = str(e)
            try:
                screenshot_path = f"{screenshot_dir}/{test.id}_error.png"
                await self.page.screenshot(path=screenshot_path)
            except:
                pass

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return TestResult(
            test_id=test.id,
            test_name=test.name,
            status=status,
            duration_ms=int(duration),
            error_message=error_message,
            screenshot_path=screenshot_path,
            steps_completed=steps_completed,
            total_steps=len(test.steps)
        )

    async def run_all(self, tests: List[TestCase], project_name: str, site_url: str, screenshot_dir: str) -> TestReport:
        """모든 테스트 실행"""
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

        start_time = datetime.now()
        results = []

        print(f"\n🧪 테스트 실행 시작: {project_name}")
        print(f"   사이트: {site_url}")
        print(f"   테스트 수: {len(tests)}")
        print("=" * 50)

        for i, test in enumerate(tests):
            print(f"\n[{i+1}/{len(tests)}] {test.name} ({test.category})")

            result = await self.run_test(test, screenshot_dir)
            results.append(result)

            status_emoji = {
                TestStatus.PASSED: "✅",
                TestStatus.FAILED: "❌",
                TestStatus.SKIPPED: "⏭️",
                TestStatus.ERROR: "💥"
            }
            print(f"  → {status_emoji[result.status]} {result.status.value} ({result.duration_ms}ms)")

            if result.error_message:
                print(f"     {result.error_message}")

        duration = (datetime.now() - start_time).total_seconds() * 1000

        report = TestReport(
            project_name=project_name,
            site_url=site_url,
            run_at=datetime.now().isoformat(),
            total_tests=len(tests),
            passed=sum(1 for r in results if r.status == TestStatus.PASSED),
            failed=sum(1 for r in results if r.status == TestStatus.FAILED),
            skipped=sum(1 for r in results if r.status == TestStatus.SKIPPED),
            error=sum(1 for r in results if r.status == TestStatus.ERROR),
            duration_ms=int(duration),
            results=results
        )

        print("\n" + "=" * 50)
        print(f"📊 테스트 완료!")
        print(f"   ✅ 성공: {report.passed}")
        print(f"   ❌ 실패: {report.failed}")
        print(f"   💥 에러: {report.error}")
        print(f"   ⏱️ 소요시간: {report.duration_ms}ms")

        return report


def parse_scenario_to_tests(scenario_markdown: str, site_url: str) -> List[TestCase]:
    """
    마크다운 시나리오를 TestCase 리스트로 변환

    예시 입력:
    | 유형 | 시나리오 | 확인 사항 | ☐ |
    |-----|---------|----------|---|
    | Happy | 1. 로그인 버튼 클릭 2. 이메일 입력 3. 비밀번호 입력 4. 제출 | 대시보드로 이동하는지 | |
    """
    tests = []

    # 테이블 행 파싱
    lines = scenario_markdown.strip().split("\n")

    test_id = 0
    for line in lines:
        if not line.startswith("|") or "유형" in line or "---" in line:
            continue

        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 3:
            continue

        category = parts[0].lower()
        scenario_text = parts[1]
        expected = parts[2]

        # 단계 파싱 (1. xxx 2. xxx 형식)
        step_pattern = r'(\d+)\.\s*([^0-9]+?)(?=\d+\.|$)'
        step_matches = re.findall(step_pattern, scenario_text)

        steps = []

        # 첫 번째 스텝: 사이트 이동
        steps.append(TestStep(
            action="navigate",
            target=site_url,
            description="사이트 이동"
        ))

        for _, step_text in step_matches:
            step_text = step_text.strip()
            step = text_to_step(step_text)
            if step:
                steps.append(step)

        if steps:
            test_id += 1
            tests.append(TestCase(
                id=f"TC{test_id:03d}",
                name=scenario_text[:50],
                category=category,
                steps=steps,
                expected=expected,
                priority="high" if category == "happy" else "medium"
            ))

    return tests


def text_to_step(text: str) -> Optional[TestStep]:
    """자연어 텍스트를 TestStep으로 변환"""
    text_lower = text.lower()

    # 클릭
    if "클릭" in text or "누르" in text or "선택" in text:
        # 버튼/링크 이름 추출 시도
        target = extract_target(text)
        return TestStep(
            action="click",
            target=target or "button",
            description=text
        )

    # 입력
    if "입력" in text or "작성" in text or "넣" in text:
        target = extract_target(text)
        value = extract_value(text)
        return TestStep(
            action="fill",
            target=target or "input",
            value=value or "테스트 입력",
            description=text
        )

    # 확인/검증
    if "확인" in text or "검증" in text or "체크" in text:
        target = extract_target(text)
        return TestStep(
            action="assert_visible",
            target=target or "body",
            description=text
        )

    # 대기
    if "기다" in text or "대기" in text or "로딩" in text:
        return TestStep(
            action="wait",
            value="2000",
            description=text
        )

    # 이동/네비게이션
    if "이동" in text or "접속" in text or "열기" in text:
        target = extract_url(text)
        return TestStep(
            action="navigate",
            target=target or "/",
            description=text
        )

    # 호버
    if "호버" in text or "마우스" in text:
        target = extract_target(text)
        return TestStep(
            action="hover",
            target=target or "button",
            description=text
        )

    # 기본: 대기
    return TestStep(
        action="wait",
        value="1000",
        description=text
    )


def extract_target(text: str) -> Optional[str]:
    """텍스트에서 선택자 추출 시도"""
    # 따옴표 안의 텍스트
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        return f"text={quoted.group(1)}"

    # 버튼 이름 패턴
    button_match = re.search(r'([\w가-힣]+)\s*(버튼|링크|탭|메뉴)', text)
    if button_match:
        return f"text={button_match.group(1)}"

    return None


def extract_value(text: str) -> Optional[str]:
    """텍스트에서 입력값 추출"""
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        return quoted.group(1)
    return None


def extract_url(text: str) -> Optional[str]:
    """텍스트에서 URL 추출"""
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        return url_match.group()
    return None


def generate_report_markdown(report: TestReport) -> str:
    """테스트 리포트를 마크다운으로 변환"""
    pass_rate = (report.passed / report.total_tests * 100) if report.total_tests > 0 else 0

    md = f"""# 🧪 QA 테스트 리포트

**프로젝트:** {report.project_name}
**사이트:** {report.site_url}
**실행 시간:** {report.run_at}
**소요 시간:** {report.duration_ms}ms

---

## 📊 요약

| 항목 | 수 |
|-----|---|
| 전체 테스트 | {report.total_tests} |
| ✅ 성공 | {report.passed} |
| ❌ 실패 | {report.failed} |
| 💥 에러 | {report.error} |
| **성공률** | **{pass_rate:.1f}%** |

---

## 📋 상세 결과

| ID | 테스트 | 상태 | 소요시간 | 진행 |
|----|--------|------|---------|------|
"""

    for r in report.results:
        status_emoji = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.SKIPPED: "⏭️",
            TestStatus.ERROR: "💥"
        }
        md += f"| {r.test_id} | {r.test_name[:30]} | {status_emoji[r.status]} | {r.duration_ms}ms | {r.steps_completed}/{r.total_steps} |\n"

    # 실패한 테스트 상세
    failed_tests = [r for r in report.results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
    if failed_tests:
        md += "\n---\n\n## ❌ 실패 상세\n\n"
        for r in failed_tests:
            md += f"### {r.test_id}: {r.test_name}\n\n"
            md += f"- **상태:** {r.status.value}\n"
            md += f"- **에러:** {r.error_message}\n"
            if r.screenshot_path:
                md += f"- **스크린샷:** {r.screenshot_path}\n"
            md += "\n"

    return md


async def run_tests(
    project_name: str,
    site_url: str,
    scenarios: str,
    output_dir: str = "./qa-test-results",
    auth_site: Optional[str] = None,
    headless: bool = True
) -> TestReport:
    """
    테스트 실행 메인 함수

    Args:
        project_name: 프로젝트 이름
        site_url: 테스트 대상 사이트 URL
        scenarios: 마크다운 형식의 시나리오
        output_dir: 결과 저장 경로
        auth_site: 인증 사이트 이름 (쿠키 사용)
        headless: 헤드리스 모드
    """
    # 시나리오 파싱
    tests = parse_scenario_to_tests(scenarios, site_url)

    if not tests:
        print("⚠️ 파싱된 테스트가 없습니다.")
        return TestReport(
            project_name=project_name,
            site_url=site_url,
            run_at=datetime.now().isoformat()
        )

    # 테스트 실행
    async with TestRunner(headless=headless, auth_site=auth_site) as runner:
        report = await runner.run_all(tests, project_name, site_url, output_dir)

    # 리포트 저장
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # JSON 저장
    report_dict = asdict(report)
    report_dict["results"] = [
        {**asdict(r), "status": r.status.value}
        for r in report.results
    ]
    with open(f"{output_dir}/report.json", "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    # 마크다운 저장
    md_report = generate_report_markdown(report)
    with open(f"{output_dir}/report.md", "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"\n📄 리포트 저장됨: {output_dir}/report.md")

    return report


def run_tests_sync(
    project_name: str,
    site_url: str,
    scenarios: str,
    output_dir: str = "./qa-test-results",
    auth_site: Optional[str] = None,
    headless: bool = True
) -> TestReport:
    """동기 버전"""
    return asyncio.run(run_tests(project_name, site_url, scenarios, output_dir, auth_site, headless))


# CLI 인터페이스
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QA Sync Test Runner")
    parser.add_argument("scenario_file", nargs="?", help="시나리오 마크다운 파일")
    parser.add_argument("--project", "-p", required=True, help="프로젝트 이름")
    parser.add_argument("--url", "-u", required=True, help="테스트 대상 URL")
    parser.add_argument("--output", "-o", default="./qa-test-results", help="결과 저장 경로")
    parser.add_argument("--auth", "-a", help="인증 사이트 이름")
    parser.add_argument("--headed", action="store_true", help="브라우저 표시 (디버깅용)")

    args = parser.parse_args()

    # 시나리오 로드
    if args.scenario_file:
        with open(args.scenario_file, "r", encoding="utf-8") as f:
            scenarios = f.read()
    else:
        # 예시 시나리오
        scenarios = """
| 유형 | 시나리오 | 확인 사항 | ☐ |
|-----|---------|----------|---|
| Happy | 1. 메인 페이지 접속 2. 로그인 버튼 클릭 | 로그인 폼이 표시되는지 | |
| Edge | 1. 빈 폼 제출 | 에러 메시지가 표시되는지 | |
"""

    # 테스트 실행
    report = run_tests_sync(
        project_name=args.project,
        site_url=args.url,
        scenarios=scenarios,
        output_dir=args.output,
        auth_site=args.auth,
        headless=not args.headed
    )

    # 종료 코드
    exit_code = 0 if report.failed == 0 and report.error == 0 else 1
    exit(exit_code)
