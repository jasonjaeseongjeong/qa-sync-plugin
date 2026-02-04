#!/usr/bin/env python3
"""
QA Sync Site Crawler
- Playwright로 사이트 UI 요소 자동 추출
- 버튼, 폼, 링크, 인터랙션 포인트 분석
- QA 시나리오 생성을 위한 데이터 제공
"""

import json
import asyncio
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: playwright not installed. Run: pip install playwright && playwright install")


@dataclass
class UIElement:
    """UI 요소 정보"""
    type: str           # button, link, input, form, etc.
    text: str           # 표시 텍스트
    selector: str       # CSS 선택자
    attributes: dict    # 추가 속성
    location: str       # 페이지 내 위치 (header, main, footer, etc.)


@dataclass
class PageAnalysis:
    """페이지 분석 결과"""
    url: str
    title: str
    buttons: list
    links: list
    forms: list
    inputs: list
    modals: list
    navigation: list
    interactive_elements: list
    screenshots: dict  # {"full": path, "viewport": path}


class SiteCrawler:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.results = []

    async def __aenter__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def analyze_page(self, url: str, screenshot_dir: Optional[str] = None) -> PageAnalysis:
        """단일 페이지 분석"""
        page = await self.browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)  # 동적 콘텐츠 로딩 대기

            title = await page.title()

            # 각 요소 타입 추출
            buttons = await self._extract_buttons(page)
            links = await self._extract_links(page, url)
            forms = await self._extract_forms(page)
            inputs = await self._extract_inputs(page)
            modals = await self._extract_modals(page)
            navigation = await self._extract_navigation(page)
            interactive = await self._extract_interactive(page)

            # 스크린샷
            screenshots = {}
            if screenshot_dir:
                from pathlib import Path
                Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

                safe_name = urlparse(url).path.replace("/", "_") or "index"
                screenshots["viewport"] = f"{screenshot_dir}/{safe_name}_viewport.png"
                screenshots["full"] = f"{screenshot_dir}/{safe_name}_full.png"

                await page.screenshot(path=screenshots["viewport"])
                await page.screenshot(path=screenshots["full"], full_page=True)

            return PageAnalysis(
                url=url,
                title=title,
                buttons=buttons,
                links=links,
                forms=forms,
                inputs=inputs,
                modals=modals,
                navigation=navigation,
                interactive_elements=interactive,
                screenshots=screenshots
            )

        finally:
            await page.close()

    async def _extract_buttons(self, page: Page) -> list:
        """버튼 요소 추출"""
        buttons = []

        # <button> 태그
        for btn in await page.query_selector_all("button"):
            text = (await btn.inner_text()).strip()
            if text:
                buttons.append({
                    "text": text[:50],
                    "selector": await self._get_selector(btn),
                    "type": await btn.get_attribute("type") or "button",
                    "disabled": await btn.is_disabled()
                })

        # role="button" 요소
        for btn in await page.query_selector_all("[role='button']"):
            text = (await btn.inner_text()).strip()
            if text and text not in [b["text"] for b in buttons]:
                buttons.append({
                    "text": text[:50],
                    "selector": await self._get_selector(btn),
                    "type": "role-button",
                    "disabled": False
                })

        # input[type="submit"]
        for btn in await page.query_selector_all("input[type='submit'], input[type='button']"):
            text = await btn.get_attribute("value") or ""
            if text:
                buttons.append({
                    "text": text[:50],
                    "selector": await self._get_selector(btn),
                    "type": "input-button",
                    "disabled": await btn.is_disabled()
                })

        return buttons[:30]  # 최대 30개

    async def _extract_links(self, page: Page, base_url: str) -> list:
        """링크 추출 (내부/외부 구분)"""
        links = []
        base_domain = urlparse(base_url).netloc

        for link in await page.query_selector_all("a[href]"):
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()

            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            full_url = urljoin(base_url, href)
            is_internal = urlparse(full_url).netloc == base_domain

            links.append({
                "text": text[:50] if text else "[no text]",
                "href": full_url,
                "internal": is_internal,
                "selector": await self._get_selector(link)
            })

        return links[:50]  # 최대 50개

    async def _extract_forms(self, page: Page) -> list:
        """폼 추출"""
        forms = []

        for form in await page.query_selector_all("form"):
            form_id = await form.get_attribute("id")
            action = await form.get_attribute("action")
            method = await form.get_attribute("method") or "GET"

            # 폼 내부 필드 수집
            fields = []
            for input_el in await form.query_selector_all("input, select, textarea"):
                field_type = await input_el.get_attribute("type") or "text"
                field_name = await input_el.get_attribute("name") or await input_el.get_attribute("id")
                placeholder = await input_el.get_attribute("placeholder")
                required = await input_el.get_attribute("required") is not None

                if field_name:
                    fields.append({
                        "name": field_name,
                        "type": field_type,
                        "placeholder": placeholder,
                        "required": required
                    })

            forms.append({
                "id": form_id,
                "action": action,
                "method": method.upper(),
                "fields": fields[:20],  # 최대 20개 필드
                "selector": await self._get_selector(form)
            })

        return forms

    async def _extract_inputs(self, page: Page) -> list:
        """폼 외부 입력 필드 추출"""
        inputs = []

        for input_el in await page.query_selector_all("input:not(form input), textarea:not(form textarea)"):
            field_type = await input_el.get_attribute("type") or "text"
            field_name = await input_el.get_attribute("name") or await input_el.get_attribute("id")
            placeholder = await input_el.get_attribute("placeholder")

            if field_name or placeholder:
                inputs.append({
                    "name": field_name,
                    "type": field_type,
                    "placeholder": placeholder,
                    "selector": await self._get_selector(input_el)
                })

        return inputs[:20]

    async def _extract_modals(self, page: Page) -> list:
        """모달/다이얼로그 추출"""
        modals = []

        selectors = [
            "[role='dialog']",
            "[role='alertdialog']",
            ".modal",
            ".dialog",
            "[class*='modal']",
            "[class*='popup']",
            "[class*='overlay']"
        ]

        for selector in selectors:
            for modal in await page.query_selector_all(selector):
                modal_id = await modal.get_attribute("id")
                aria_label = await modal.get_attribute("aria-label")
                is_visible = await modal.is_visible()

                modals.append({
                    "id": modal_id,
                    "label": aria_label,
                    "visible": is_visible,
                    "selector": selector
                })

        return modals

    async def _extract_navigation(self, page: Page) -> list:
        """네비게이션 요소 추출"""
        nav_items = []

        for nav in await page.query_selector_all("nav, [role='navigation']"):
            for link in await nav.query_selector_all("a"):
                text = (await link.inner_text()).strip()
                href = await link.get_attribute("href")

                if text:
                    nav_items.append({
                        "text": text[:30],
                        "href": href
                    })

        return nav_items[:20]

    async def _extract_interactive(self, page: Page) -> list:
        """기타 인터랙티브 요소 추출"""
        interactive = []

        # 드롭다운
        for el in await page.query_selector_all("select, [role='listbox'], [role='combobox']"):
            label = await el.get_attribute("aria-label") or await el.get_attribute("name")
            interactive.append({"type": "dropdown", "label": label})

        # 탭
        for el in await page.query_selector_all("[role='tablist']"):
            tabs = await el.query_selector_all("[role='tab']")
            tab_names = [await t.inner_text() for t in tabs]
            interactive.append({"type": "tabs", "items": tab_names[:10]})

        # 토글/스위치
        for el in await page.query_selector_all("[role='switch'], [type='checkbox']"):
            label = await el.get_attribute("aria-label") or await el.get_attribute("name")
            interactive.append({"type": "toggle", "label": label})

        # 슬라이더
        for el in await page.query_selector_all("[role='slider'], input[type='range']"):
            label = await el.get_attribute("aria-label") or await el.get_attribute("name")
            interactive.append({"type": "slider", "label": label})

        return interactive[:30]

    async def _get_selector(self, element) -> str:
        """요소의 고유 선택자 생성"""
        # ID가 있으면 사용
        el_id = await element.get_attribute("id")
        if el_id:
            return f"#{el_id}"

        # data-testid 사용
        testid = await element.get_attribute("data-testid")
        if testid:
            return f"[data-testid='{testid}']"

        # 클래스 기반
        classes = await element.get_attribute("class")
        if classes:
            main_class = classes.split()[0]
            return f".{main_class}"

        return ""

    def to_markdown(self, analysis: PageAnalysis) -> str:
        """분석 결과를 마크다운으로 변환"""
        md = f"# 페이지 분석: {analysis.title}\n\n"
        md += f"**URL:** {analysis.url}\n\n"

        if analysis.buttons:
            md += "## 버튼\n\n"
            md += "| 텍스트 | 타입 | 선택자 |\n|--------|------|--------|\n"
            for btn in analysis.buttons:
                md += f"| {btn['text']} | {btn['type']} | `{btn['selector']}` |\n"
            md += "\n"

        if analysis.forms:
            md += "## 폼\n\n"
            for form in analysis.forms:
                md += f"### {form['id'] or '(no id)'}\n"
                md += f"- Method: {form['method']}\n"
                md += f"- Action: {form['action']}\n"
                md += "- Fields:\n"
                for field in form['fields']:
                    req = " (필수)" if field['required'] else ""
                    md += f"  - `{field['name']}` ({field['type']}){req}\n"
                md += "\n"

        if analysis.navigation:
            md += "## 네비게이션\n\n"
            for nav in analysis.navigation:
                md += f"- [{nav['text']}]({nav['href']})\n"
            md += "\n"

        if analysis.interactive_elements:
            md += "## 인터랙티브 요소\n\n"
            for el in analysis.interactive_elements:
                md += f"- **{el['type']}**: {el.get('label') or el.get('items', '')}\n"
            md += "\n"

        if analysis.links:
            internal = [l for l in analysis.links if l['internal']]
            external = [l for l in analysis.links if not l['internal']]

            md += f"## 링크 (내부: {len(internal)}, 외부: {len(external)})\n\n"
            md += "### 주요 내부 링크\n"
            for link in internal[:10]:
                md += f"- [{link['text']}]({link['href']})\n"
            md += "\n"

        return md


async def crawl_site(url: str, screenshot_dir: Optional[str] = None) -> dict:
    """사이트 크롤링 메인 함수"""
    async with SiteCrawler(headless=True) as crawler:
        analysis = await crawler.analyze_page(url, screenshot_dir)
        return {
            "analysis": asdict(analysis) if hasattr(analysis, '__dataclass_fields__') else analysis.__dict__,
            "markdown": crawler.to_markdown(analysis)
        }


def crawl_site_sync(url: str, screenshot_dir: Optional[str] = None) -> dict:
    """동기 버전 (CLI용)"""
    return asyncio.run(crawl_site(url, screenshot_dir))


# CLI 인터페이스
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: site_crawler.py <url> [screenshot_dir]")
        print("Example: site_crawler.py https://example.com ./screenshots")
        sys.exit(1)

    url = sys.argv[1]
    screenshot_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if not PLAYWRIGHT_AVAILABLE:
        print("Error: playwright not installed")
        print("Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"Crawling {url}...")
    result = crawl_site_sync(url, screenshot_dir)

    print("\n" + "=" * 50)
    print(result["markdown"])

    # JSON 출력
    if screenshot_dir:
        json_path = f"{screenshot_dir}/analysis.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result["analysis"], f, ensure_ascii=False, indent=2)
        print(f"\nJSON saved to: {json_path}")
