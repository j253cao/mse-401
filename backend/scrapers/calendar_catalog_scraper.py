"""
Scraper for the University of Waterloo Undergraduate Academic Calendar catalog.
Visits the programs/minors index and each program page, then stores structured data.

Target: https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog#/programs?expanded=
Program example: Accounting and Financial Management (Honours) etc.
"""

import json
import re
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

# Playwright is optional at import; we check at runtime
try:
    from playwright.sync_api import sync_playwright, Page, Browser
except ImportError:
    sync_playwright = None


# Base URL of the catalog (no hash)
CATALOG_BASE = "https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog"
PROGRAMS_INDEX_HASH = "#/programs?expanded="
# Search URL: shows only programs matching "minor" (no accordion expansion needed)
PROGRAMS_SEARCH_MINOR_HASH = "#/programs?searchTerm=minor"

# Engineering Options page: table of options with links to catalog
ENGINEERING_OPTIONS_URL = "https://uwaterloo.ca/engineering/undergraduate-students/degree-enhancement/options"

# Fallback: known minor URLs when the catalog SPA doesn't expose links (e.g. slow render, different DOM).
# Format: (url, display_name). Add more from the calendar as needed.
KNOWN_MINOR_URLS: List[tuple[str, str]] = [
    (
        f"{CATALOG_BASE}#/programs/S1mSkJ00o3?expanded=&bc=true&bcCurrent=Biochemistry%20Minor&bcGroup=Biochemistry&bcItemType=programs",
        "Biochemistry Minor",
    ),
]


def get_data_dir() -> Path:
    """Return path to data/programs directory (repo root relative to backend)."""
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent
    return repo_root / "data" / "programs"


def slugify(s: str) -> str:
    """Make a safe filename slug from a string."""
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:120] if s else "unnamed"


# Course code pattern: SUBJ + digits (e.g. AFM111, ECON101, COMMST111)
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s*(\d{3})\b")


def _normalize_course_code(match: re.Match) -> str:
    """Normalize to 'SUBJ NNN' (e.g. AFM 111) then return 'SUBJNNN' for consistency."""
    subj, num = match.group(1), match.group(2)
    return f"{subj}{num}"


def parse_course_lists_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse course requirements text into a list of {list_description, required_count, courses}.
    Handles "Complete all of the following", "Complete N of the following", and extracts course codes.
    """
    lists_out: List[Dict[str, Any]] = []
    complete_all_re = re.compile(
        r"Complete\s+all\s+(?:of\s+)?the\s+following\s*:?\s*",
        re.IGNORECASE
    )
    complete_n_re = re.compile(
        r"Complete\s+(\d+)\s+of\s+the\s+following\s*:?\s*",
        re.IGNORECASE
    )
    # Next section = next line that looks like "Complete ... following" (so we don't split mid-block)
    next_section_start_re = re.compile(
        r"\n\s*Complete\s+(?:all\s+(?:of\s+)?the\s+following|\d+\s+of\s+the\s+following)\s*:?\s*",
        re.IGNORECASE
    )

    remaining = text
    while remaining:
        best_start = len(remaining)
        best_match = None
        best_desc = ""
        best_n = 0

        for pattern, desc, n in [
            (complete_all_re, "Complete all the following", 0),
            (complete_n_re, None, -1),
        ]:
            m = pattern.search(remaining)
            if m and m.start() < best_start:
                best_start = m.start()
                best_match = m
                best_desc = desc or m.group(0).strip().rstrip(":")
                best_n = n if n != -1 else int(m.group(1))

        if best_match is None:
            break
        section_start = best_match.end()
        next_m = next_section_start_re.search(remaining[section_start:])
        next_section = section_start + next_m.start() if next_m else len(remaining)
        body = remaining[section_start:next_section]
        remaining = remaining[next_section:].lstrip()
        desc = best_desc or "Complete N of the following"
        if best_n == 0:
            desc = "Complete all the following"
        codes = []
        for m in COURSE_CODE_RE.finditer(body):
            code = _normalize_course_code(m)
            if code not in codes:
                codes.append(code)
        if not codes:
            continue
        required_count = len(codes) if best_n == 0 else best_n
        lists_out.append({
            "list_description": desc,
            "required_count": required_count,
            "courses": codes,
        })
    return lists_out


def raw_to_program_output(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reduce full scraped program/minor page data to only program_name and course_lists.
    Used for all saved JSON so minors and programs share the same format.
    """
    # Program name: prefer raw main content line that looks like the program title, else index_name, else title
    program_name = ""
    if raw_data.get("index_name"):
        program_name = raw_data["index_name"].strip()
    if raw_data.get("raw_sections"):
        for sec in raw_data["raw_sections"]:
            main = sec.get("main_content", "")
            # First line after "Print this page" that looks like a program name (contains parenthesis or "Bachelor"/"Minor")
            for line in main.split("\n"):
                line = line.strip()
                if not line or line == "Print this page" or "Academic Calendar" in line:
                    continue
                if ("(" in line and ")" in line) or "Bachelor" in line or "Minor" in line or "Honours" in line:
                    program_name = line
                    break
            if program_name:
                break
    if not program_name and raw_data.get("title"):
        program_name = raw_data["title"].strip()

    course_lists: List[Dict[str, Any]] = []
    # Prefer full course requirements text
    cr = raw_data.get("course_requirements") or {}
    full_text = cr.get("course_requirements") or ""
    if not full_text and cr.get("course_blocks"):
        full_text = "\n".join(
            b.get("text", "") for b in cr["course_blocks"] if isinstance(b, dict)
        )
    if not full_text and raw_data.get("raw_sections"):
        for sec in raw_data["raw_sections"]:
            full_text = sec.get("main_content", "") or ""
            if "Course Requirements" in full_text or "Complete all" in full_text:
                break
    if full_text:
        course_lists = parse_course_lists_from_text(full_text)

    return {
        "program_name": program_name or "Unknown",
        "course_lists": course_lists,
    }


class CalendarCatalogScraper:
    """
    Scrapes the UW Undergraduate Academic Calendar catalog:
    1. Opens the programs index and collects all program/minor links.
    2. Visits each link and extracts structured data (title, admission, graduation, courses, etc.).
    3. Saves each program to data/programs/ as JSON.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        headless: bool = True,
        delay_between_pages: float = 1.0,
    ):
        self.output_dir = Path(output_dir) if output_dir else get_data_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.delay_between_pages = delay_between_pages
        self._playwright = None
        self._browser: Optional[Browser] = None

    def _ensure_playwright(self) -> None:
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright is required. Install with: pip install playwright && playwright install chromium"
            )

    def _get_index_url(self) -> str:
        return f"{CATALOG_BASE}{PROGRAMS_INDEX_HASH}"

    def _collect_minor_links_by_expanding_each_section(self, page: Page) -> List[Dict[str, str]]:
        """
        Expand each accordion section one by one; after each expand, look for
        links whose text contains "Minor" in the newly visible content and collect them.
        Returns list of {url, href, name} for minor links only.
        """
        seen_hrefs: set[str] = set()
        minor_links: List[Dict[str, str]] = []

        def harvest_minor_links() -> None:
            """Collect any visible program links that contain 'Minor' in their text or URL."""
            try:
                items = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('a[href*="#/programs/"]').forEach(a => {
                        const href = (a.getAttribute('href') || '').trim();
                        if (!href) return;
                        const rest = href.split('#/programs/')[1];
                        if (!rest || rest.split('?')[0].trim() === '' || rest.startsWith('?')) return;
                        const name = (a.textContent || '').trim();
                        if (name.toLowerCase().indexOf('minor') === -1 && href.toLowerCase().indexOf('minor') === -1) return;
                        out.push({ href, name });
                    });
                    return out;
                }""")
                for item in (items or []):
                    href = (item.get("href") or "").strip()
                    name = (item.get("name") or "").strip()
                    if not href or href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)
                    full_url = f"{CATALOG_BASE}{href}" if href.startswith("#") else href
                    minor_links.append({"url": full_url, "href": href, "name": name})
            except Exception:
                pass

        time.sleep(2)
        # Harvest any minors already visible (e.g. from previous run or default expanded)
        harvest_minor_links()

        # Find all accordion headers / expandable section buttons
        selectors = [
            "[aria-expanded]",
            "[class*='AccordionSummary']",
            "[class*='accordionSummary']",
            "[class*='MuiAccordion'] button",
            "button[aria-controls]",
            "[role='button']",
        ]
        clicked_count = 0
        for selector in selectors:
            try:
                els = page.locator(selector)
                n = els.count()
                if n == 0:
                    continue
                for i in range(min(n, 200)):
                    try:
                        el = els.nth(i)
                        if not el.is_visible():
                            continue
                        # Skip tiny icons (e.g. chevron inside the same section)
                        box = el.bounding_box()
                        if box and (box.get("width", 0) < 80 or box.get("height", 0) < 15):
                            continue
                        el.scroll_into_view_if_needed()
                        time.sleep(0.25)
                        el.click()
                        clicked_count += 1
                        time.sleep(0.6)  # Let new content render
                        harvest_minor_links()
                    except Exception:
                        continue
                if clicked_count > 0:
                    break
            except Exception:
                continue

        return minor_links

    def _expand_all_accordion_sections(self, page: Page) -> None:
        """Expand all accordion sections at once (fallback when expand-one-by-one finds no minors)."""
        time.sleep(2)
        try:
            collapsed = page.locator("[aria-expanded='false']")
            for i in range(collapsed.count()):
                try:
                    el = collapsed.nth(i)
                    el.scroll_into_view_if_needed()
                    time.sleep(0.2)
                    el.click()
                    time.sleep(0.5)
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(1.5)

    def _collect_options_links(self, page: Page) -> List[Dict[str, str]]:
        """
        Load the Engineering Options page and collect all links to the academic calendar
        catalog (#/programs/...). Returns list of {url, href, name} for each option.
        """
        page.goto(ENGINEERING_OPTIONS_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        links: List[Dict[str, str]] = []
        seen: set[str] = set()
        # Links to catalog: full URL or path containing catalog#/programs/
        for el in page.locator("a[href*='catalog'][href*='#/programs/'], a[href*='academic-calendar'][href*='programs']").all():
            try:
                href = (el.get_attribute("href") or "").strip()
                if not href or href in seen:
                    continue
                # Normalize to full catalog URL
                if href.startswith("http"):
                    url = href
                elif href.startswith("#"):
                    url = f"{CATALOG_BASE}{href}"
                else:
                    url = urljoin(ENGINEERING_OPTIONS_URL, href)
                if "#/programs/" not in url:
                    continue
                rest = url.split("#/programs/")[-1].split("?")[0].strip("/")
                if not rest or rest == "programs":
                    continue
                name = (el.inner_text() or "").strip()
                if not name or len(name) > 150:
                    name = ""
                seen.add(href)
                links.append({"url": url, "href": href, "name": name or rest})
            except Exception:
                continue
        return links

    def _collect_program_links(self, page: Page, minors_only: bool = False) -> List[Dict[str, str]]:
        """Load the programs index and return list of {url, name} for each program/minor link.
        If minors_only is True: use the catalog search URL ?searchTerm=minor so the page lists
        only minors; then collect all program links from that page (no accordion expansion)."""
        if minors_only:
            index_url = f"{CATALOG_BASE}{PROGRAMS_SEARCH_MINOR_HASH}"
            print("Loading catalog search: ?searchTerm=minor")
        else:
            index_url = self._get_index_url()
        page.goto(index_url, wait_until="domcontentloaded", timeout=60000)
        # Wait for SPA to render (search results or program list)
        try:
            page.wait_for_selector("a[href*='#/programs/']", timeout=25000)
        except Exception:
            pass
        time.sleep(4 if minors_only else 3)  # Extra time for search results to render

        if minors_only:
            # Search page: scroll to load all results (SPA may lazy-load), then collect links
            for _ in range(15):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.8)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(0.4)
            time.sleep(2)
            # Collect all program links (they are the minor search results)
            links = self._collect_links_from_page(page)
            if links:
                return links
            # Fallback: try expand-each-section then collect
            links = self._collect_minor_links_by_expanding_each_section(page)
            if links:
                return links
            self._expand_all_accordion_sections(page)

        links = self._collect_links_from_page(page)
        if minors_only and links:
            links = [
                item for item in links
                if "minor" in (item.get("name") or "").lower() or "minor" in (item.get("url") or "").lower()
            ]
        return links

    def _collect_links_from_page(self, page: Page) -> List[Dict[str, str]]:
        """Collect all program links (#/programs/<id>) currently visible on the page."""
        links: List[Dict[str, str]] = []
        seen_hrefs: set[str] = set()

        def add_link(el: Any, href: str, name_override: Optional[str] = None) -> None:
            if not href or href in seen_hrefs:
                return
            if re.match(r"#/programs\?expanded=$", href) or href == "#/programs" or href.endswith("#/programs"):
                return
            if "?searchTerm=" in href and "#/programs/" not in href.replace("?searchTerm=", ""):
                return
            if "#/programs/" in href:
                rest = href.split("#/programs/")[-1].split("?")[0].strip("/")
                if not rest or rest == "programs":
                    return
            text = name_override if name_override is not None else (el.inner_text().strip() if hasattr(el, "inner_text") else "")
            seen_hrefs.add(href)
            full_url = href if href.startswith("http") else f"{CATALOG_BASE}{href}"
            links.append({"url": full_url, "href": href, "name": text or ""})

        # Primary: links with #/programs/<id>
        for selector in ["a[href*='#/programs/']", "a[href*=\"#/programs/\"]", "[href*='#/programs/']"]:
            try:
                anchor = page.locator(selector)
                n = anchor.count()
                for i in range(n):
                    el = anchor.nth(i)
                    href = el.get_attribute("href") or ""
                    add_link(el, href)
                if links:
                    break
            except Exception:
                continue

        # Fallback: any anchor with programs in href
        if not links:
            try:
                all_a = page.locator("a[href*='programs']")
                for i in range(all_a.count()):
                    el = all_a.nth(i)
                    href = el.get_attribute("href") or ""
                    if "#/programs/" in href:
                        add_link(el, href)
            except Exception:
                pass

        # Fallback: all links, filter by href pattern
        if not links:
            try:
                for el in page.locator("a[href]").all():
                    href = el.get_attribute("href") or ""
                    if "#/programs/" in href and "?" not in href.split("#")[-1].split("/")[0]:
                        add_link(el, href)
            except Exception:
                pass

        # Fallback: use JS to get all hrefs from DOM (catches SPA-rendered links)
        if not links:
            try:
                hrefs_and_text = page.evaluate("""() => {
                    const out = [];
                    document.querySelectorAll('a[href*="#/programs/"]').forEach(a => {
                        const href = (a.getAttribute('href') || '').trim();
                        if (!href) return;
                        const rest = href.split('#/programs/')[1];
                        if (!rest || rest.split('?')[0].trim() === '' || rest.startsWith('?')) return;
                        out.push({ href, name: (a.textContent || '').trim() });
                    });
                    return out;
                }""")
                for item in hrefs_and_text or []:
                    href = (item.get("href") or "").strip()
                    name = (item.get("name") or "").strip()
                    if not href or href in seen_hrefs:
                        continue
                    if re.match(r"#/programs\?expanded=$", href) or href == "#/programs":
                        continue
                    rest = href.split("#/programs/")[-1].split("?")[0].strip("/")
                    if not rest or rest == "programs":
                        continue
                    seen_hrefs.add(href)
                    full_url = f"{CATALOG_BASE}{href}" if href.startswith("#") else href
                    links.append({"url": full_url, "href": href, "name": name})
            except Exception:
                pass

        # Fallback: parse raw HTML for hrefs
        if not links:
            try:
                html = page.content()
                for m in re.finditer(r'href\s*=\s*["\']([^"\']*#/programs/([^"\'?]+)[^"\']*)["\']', html):
                    href = m.group(1).strip()
                    rest = (m.group(2) or "").strip("/")
                    if not rest or rest == "programs":
                        continue
                    if href in seen_hrefs:
                        continue
                    seen_hrefs.add(href)
                    full_url = f"{CATALOG_BASE}{href}" if href.startswith("#") else (href if href.startswith("http") else href)
                    links.append({"url": full_url, "href": href, "name": ""})
            except Exception:
                pass

        return links

    def _extract_text_section(self, page: Page, heading_text: str) -> Optional[str]:
        """Get body text for a section that follows a heading containing heading_text."""
        try:
            h = page.get_by_role("heading", name=re.compile(re.escape(heading_text), re.I))
            if h.count() == 0:
                return None
            first = h.first
            parent = first.locator("xpath=..")
            return parent.inner_text().strip()
        except Exception:
            return None

    def _extract_course_blocks(self, page: Page) -> List[Dict[str, Any]]:
        """Extract required/elective course blocks (e.g. 'Complete all of the following')."""
        blocks: List[Dict[str, Any]] = []
        # Look for list items or divs that contain course codes like AFM111, ECON101
        course_code = re.compile(r"[A-Z]{2,4}\s*\d{3}")
        # Sections that often contain course lists
        for selector in ["[class*='requirement']", "[class*='course']", "li", ".content"]:
            try:
                els = page.locator(selector).all()
                for el in els:
                    text = el.inner_text()
                    if not text or len(text) > 5000:
                        continue
                    if course_code.search(text):
                        blocks.append({"text": text.strip()[:2000]})
            except Exception:
                continue
        return blocks[:50]

    def _extract_program_page(self, page: Page, url: str) -> Dict[str, Any]:
        """Extract structured data from a single program/minor page."""
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(1.5)

        data: Dict[str, Any] = {
            "url": url,
            "title": "",
            "breadcrumb": "",
            "system_of_study": [],
            "admission_requirements": {},
            "graduation_requirements": {},
            "study_work_sequence": {},
            "course_requirements": {},
            "raw_sections": [],
        }

        # Title: usually h1 or main heading
        try:
            h1 = page.locator("h1").first
            if h1.count() > 0:
                data["title"] = h1.inner_text().strip()
        except Exception:
            pass

        # Breadcrumb
        try:
            nav = page.locator("[class*='breadcrumb'], nav, [aria-label='Breadcrumb']").first
            if nav.count() > 0:
                data["breadcrumb"] = nav.inner_text().strip()
        except Exception:
            pass

        # System of study (e.g. Co-operative, Regular)
        try:
            for el in page.get_by_text("Systems of Study", exact=False).all():
                parent = el.locator("xpath=..")
                text = parent.inner_text()
                if "Co-operative" in text:
                    data["system_of_study"].append("Co-operative")
                if "Regular" in text:
                    data["system_of_study"].append("Regular")
            if not data["system_of_study"]:
                body = page.locator("body").inner_text()
                if "Co-operative" in body:
                    data["system_of_study"].append("Co-operative")
                if "Regular" in body:
                    data["system_of_study"].append("Regular")
        except Exception:
            pass

        # Admission requirements
        try:
            for heading in ["Admission Requirements", "Minimum Requirements", "Minimum Average(s) Required"]:
                text = self._extract_text_section(page, heading)
                if text:
                    key = heading.lower().replace(" ", "_").replace("(", "").replace(")", "")
                    data["admission_requirements"][key] = text[:3000]
        except Exception:
            pass

        # Graduation requirements
        try:
            for heading in [
                "Graduation Requirements",
                "Unit Requirements",
                "Undergraduate Communication Requirement",
                "Co-operative Education Program Requirements",
                "Notes",
            ]:
                text = self._extract_text_section(page, heading)
                if text:
                    key = heading.lower().replace(" ", "_").replace("(", "").replace(")", "")
                    data["graduation_requirements"][key] = text[:3000]
        except Exception:
            pass

        # Study/Work sequence table
        try:
            table = page.locator("table").first
            if table.count() > 0:
                rows: List[List[str]] = []
                for tr in table.locator("tr").all():
                    cells = tr.locator("th, td").all_inner_texts()
                    rows.append([c.strip() for c in cells])
                data["study_work_sequence"]["table"] = rows
            legend = self._extract_text_section(page, "Legend for Study/Work Sequence")
            if legend:
                data["study_work_sequence"]["legend"] = legend[:2000]
        except Exception:
            pass

        # Course requirements
        try:
            for heading in [
                "Course Requirements",
                "Required Courses",
                "Complete all of the following",
                "Additional Constraints",
                "Specializations",
            ]:
                text = self._extract_text_section(page, heading)
                if text:
                    key = heading.lower().replace(" ", "_").replace(",", "")
                    data["course_requirements"][key] = text[:4000]
            blocks = self._extract_course_blocks(page)
            if blocks:
                data["course_requirements"]["course_blocks"] = blocks
        except Exception:
            pass

        # Raw main content for backup parsing
        try:
            main = page.locator("main, [role='main'], .main-content, #main, .content").first
            if main.count() > 0:
                data["raw_sections"].append({"main_content": main.inner_text().strip()[:8000]})
        except Exception:
            pass

        return data

    def run(
        self,
        program_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
        minors_only: bool = False,
        options_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Run the full scrape: index -> all program links -> scrape each -> save to output_dir.
        If options_only is True: load Engineering Options page, collect catalog links, scrape each -> all_options.json.
        If minors_only is True: load catalog search ?searchTerm=minor, collect links, scrape each -> all_programs.json.
        If program_filter is set, only scrape links whose name or url contains any of the strings.
        If limit is set, only scrape the first N matching links.
        """
        self._ensure_playwright()
        results: List[Dict[str, Any]] = []

        with sync_playwright() as p:
            self._browser = p.chromium.launch(headless=self.headless)
            context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                if options_only:
                    print("Loading Engineering Options page...")
                    links = self._collect_options_links(page)
                else:
                    links = self._collect_program_links(page, minors_only=bool(minors_only))
            finally:
                context.close()
                self._browser.close()

        if not links and not options_only and minors_only and KNOWN_MINOR_URLS:
            # Fallback: use known minor URLs when catalog didn't expose links
            links = [{"url": url, "href": url, "name": name} for url, name in KNOWN_MINOR_URLS]
            print(f"Using {len(links)} known minor URL(s) (catalog links not found).")

        if not links:
            # Save empty index and return
            index_path = self.output_dir / ("options_index.json" if options_only else "programs_index.json")
            index_path.write_text(json.dumps({"links": [], "note": "No links found."}, indent=2), encoding="utf-8")
            return results

        # Filter and optionally limit
        filtered = []
        for item in links:
            name = item.get("name") or "unknown"
            url = item["url"]
            if program_filter:
                if not any(f.lower() in name.lower() or f.lower() in url.lower() for f in program_filter):
                    continue
            filtered.append(item)
            if limit is not None and len(filtered) >= limit:
                break

        # Save index of links (filtered set we will scrape)
        index_path = self.output_dir / ("options_index.json" if options_only else "programs_index.json")
        index_path.write_text(json.dumps({"links": filtered, "count": len(filtered)}, indent=2), encoding="utf-8")

        for i, item in enumerate(filtered):
            name = item.get("name") or "unknown"
            url = item["url"]
            print(f"[{i+1}/{len(filtered)}] Scraping: {name[:60]}...")
            with sync_playwright() as p:
                self._browser = p.chromium.launch(headless=self.headless)
                context = self._browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()
                try:
                    raw_data = self._extract_program_page(page, url)
                    raw_data["index_name"] = name
                    program_data = raw_to_program_output(raw_data)
                    if options_only:
                        program_data["option_name"] = program_data.pop("program_name", program_data.get("program_name", ""))
                    results.append(program_data)
                except Exception as e:
                    print(f"  Error: {e}")
                    results.append(
                        {"option_name" if options_only else "program_name": name, "course_lists": [], "error": str(e)}
                    )
                finally:
                    context.close()
                    self._browser.close()
            time.sleep(self.delay_between_pages)

        # Combined output
        combined_path = self.output_dir / ("all_options.json" if options_only else "all_programs.json")
        combined_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return results

    def run_single_page(self, url: str, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape a single program/minor page and save to a JSON file.
        Returns the scraped data dict.
        """
        self._ensure_playwright()
        with sync_playwright() as p:
            self._browser = p.chromium.launch(headless=self.headless)
            context = self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            try:
                raw_data = self._extract_program_page(page, url)
                raw_data["index_name"] = raw_data.get("index_name") or ""
                data = raw_to_program_output(raw_data)
                if output_filename:
                    out_path = self.output_dir / output_filename
                else:
                    out_path = self.output_dir / "single_program.json"
                out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return data
            finally:
                context.close()
                self._browser.close()


def main():
    """CLI entrypoint: run scraper and write to data/programs/."""
    import argparse
    parser = argparse.ArgumentParser(description="Scrape UW Undergraduate Academic Calendar programs/minors.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory (default: data/programs)")
    parser.add_argument("--no-headless", action="store_true", help="Show browser window")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between page requests")
    parser.add_argument("--filter", nargs="*", help="Only scrape programs whose name/url contains any of these strings")
    parser.add_argument("--limit", type=int, default=None, help="Only scrape the first N matching links (e.g. 5 for top 5 minors)")
    parser.add_argument("--minors-only", action="store_true", help="Use catalog search ?searchTerm=minor and scrape all minors -> all_programs.json")
    parser.add_argument("--options-only", action="store_true", help="Scrape Engineering Options from degree-enhancement/options -> all_options.json")
    parser.add_argument("--single-url", metavar="URL", help="Scrape only this one page and save to data/programs/single_program.json")
    args = parser.parse_args()
    scraper = CalendarCatalogScraper(
        output_dir=args.output_dir,
        headless=not args.no_headless,
        delay_between_pages=args.delay,
    )
    if args.single_url:
        data = scraper.run_single_page(args.single_url)
        out_file = scraper.output_dir / "single_program.json"
        print(f"Done. Saved 1 program to {out_file}")
    else:
        results = scraper.run(
            program_filter=args.filter,
            limit=args.limit,
            minors_only=args.minors_only,
            options_only=args.options_only,
        )
        out_name = "options" if args.options_only else "programs"
        print(f"Done. Scraped {len(results)} {out_name} to {scraper.output_dir}")


if __name__ == "__main__":
    main()
