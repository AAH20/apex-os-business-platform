"""
Comprehensive accessibility tests for APEX-OS Business Platform.
Tests ARIA labels, keyboard navigation, color contrast,
screen reader compatibility, and focus management.
"""
import asyncio
import re
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"
PAGES = ["/", "/dashboard", "/projects", "/settings", "/profile", "/reports"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def fetch_page(path: str) -> BeautifulSoup:
    """Fetch a page and return parsed HTML."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        resp = await client.get(path)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")


def get_all_interactive(soup: BeautifulSoup) -> list:
    """Return all interactive elements (links, buttons, inputs, selects)."""
    selectors = "a[href], button, input, select, textarea, [tabindex]"
    return soup.select(selectors)


def has_aria_label(el) -> bool:
    """Check if element has an accessible name via aria-label, aria-labelledby, or text."""
    if el.get("aria-label", "").strip():
        return True
    if el.get("aria-labelledby", "").strip():
        return True
    if el.name in ("input", "textarea") and el.get("placeholder", "").strip():
        return True
    if el.name == "a" and el.get_text(strip=True):
        return True
    if el.name == "button" and el.get_text(strip=True):
        return True
    return False


def luminance(hex_color: str) -> float:
    """Calculate relative luminance of a hex color."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    l1, l2 = luminance(color1), luminance(color2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# 1. ARIA Labels
# ---------------------------------------------------------------------------

class TestAriaLabels:
    """Test that all pages have proper ARIA labels."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_page_has_lang_attribute(self, path):
        """Every page must declare a language."""
        soup = await fetch_page(path)
        html_tag = soup.find("html")
        assert html_tag and html_tag.get("lang"), f"{path}: missing <html lang>"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_page_has_title(self, path):
        """Every page must have a non-empty <title>."""
        soup = await fetch_page(path)
        title = soup.find("title")
        assert title and title.get_text(strip=True), f"{path}: missing <title>"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_interactive_elements_have_accessible_names(self, path):
        """All interactive elements must have an accessible name."""
        soup = await fetch_page(path)
        interactive = get_all_interactive(soup)
        unnamed = [str(el) for el in interactive if not has_aria_label(el)]
        assert not unnamed, f"{path}: {len(unnamed)} elements lack accessible names"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_images_have_alt_text(self, path):
        """All <img> elements must have alt attributes."""
        soup = await fetch_page(path)
        images = soup.find_all("img")
        missing_alt = [str(img) for img in images if not img.get("alt") is not None]
        assert not missing_alt, f"{path}: {len(missing_alt)} images missing alt"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_landmarks_present(self, path):
        """Pages should use ARIA landmarks (header, nav, main, footer)."""
        soup = await fetch_page(path)
        landmarks = soup.select("header, nav, main, footer, [role=main], [role=navigation]")
        assert landmarks, f"{path}: no landmark elements found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_form_inputs_have_labels(self, path):
        """Every form input must have an associated label."""
        soup = await fetch_page(path)
        inputs = soup.find_all(["input", "select", "textarea"])
        unlabeled = []
        for inp in inputs:
            input_id = inp.get("id")
            if input_id and soup.find("label", attrs={"for": input_id}):
                continue
            if inp.get("aria-label") or inp.get("aria-labelledby"):
                continue
            if inp.get("type") in ("hidden", "submit", "button"):
                continue
            unlabeled.append(str(inp))
        assert not unlabeled, f"{path}: {len(unlabeled)} inputs missing labels"


# ---------------------------------------------------------------------------
# 2. Keyboard Navigation
# ---------------------------------------------------------------------------

class TestKeyboardNavigation:
    """Test keyboard navigation support."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_no_positive_tabindex(self, path):
        """No element should have tabindex > 0 (anti-pattern)."""
        soup = await fetch_page(path)
        bad = [str(el) for el in soup.select("[tabindex]") if int(el.get("tabindex", 0)) > 0]
        assert not bad, f"{path}: positive tabindex found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_links_are_focusable(self, path):
        """All links should be keyboard-focusable (no tabindex=-1)."""
        soup = await fetch_page(path)
        links = soup.select("a[href]")
        unfocusable = [str(a) for a in links if a.get("tabindex") == "-1"]
        assert not unfocusable, f"{path}: {len(unfocusable)} links not focusable"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_buttons_are_focusable(self, path):
        """All buttons should be keyboard-focusable."""
        soup = await fetch_page(path)
        buttons = soup.find_all("button")
        unfocusable = [str(b) for b in buttons if b.get("tabindex") == "-1" or b.get("disabled")]
        assert not unfocusable, f"{path}: {len(unfocusable)} buttons not focusable"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_skip_link_present(self, path):
        """Pages should have a skip-to-content link."""
        soup = await fetch_page(path)
        skip = soup.select("a[href^='#']")
        has_skip = any("skip" in a.get_text().lower() or "skip" in str(a.get("class", "")).lower() for a in skip)
        assert has_skip, f"{path}: no skip navigation link found"


# ---------------------------------------------------------------------------
# 3. Color Contrast
# ---------------------------------------------------------------------------

class TestColorContrast:
    """Test WCAG color contrast requirements."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_inline_styles_have_contrast(self, path):
        """Inline-styled text must meet WCAG AA (4.5:1)."""
        soup = await fetch_page(path)
        elements = soup.find_all(style=True)
        failures = []
        for el in elements:
            style = el.get("style", "")
            color_match = re.search(r"color:\s*(#[0-9a-fA-F]{3,6})", style)
            bg_match = re.search(r"background(?:-color)?:\s*(#[0-9a-fA-F]{3,6})", style)
            if color_match and bg_match:
                ratio = contrast_ratio(color_match.group(1), bg_match.group(1))
                if ratio < 4.5:
                    failures.append(f"{el.name}: ratio {ratio:.2f}")
        assert not failures, f"{path}: contrast failures: {failures}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_css_files_exist(self, path):
        """Referenced CSS files should be accessible."""
        soup = await fetch_page(path)
        css_links = soup.select("link[rel=stylesheet]")
        for link in css_links:
            href = link.get("href", "")
            if href.startswith("http"):
                continue
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
                resp = await client.get(href)
                assert resp.status_code == 200, f"{path}: CSS {href} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# 4. Screen Reader Compatibility
# ---------------------------------------------------------------------------

class TestScreenReader:
    """Test screen reader compatibility."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_heading_hierarchy(self, path):
        """Headings should not skip levels (h1 -> h3 is invalid)."""
        soup = await fetch_page(path)
        headings = soup.find_all(re.compile("^h[1-6]$"))
        prev_level = 0
        skips = []
        for h in headings:
            level = int(h.name[1])
            if prev_level and level > prev_level + 1:
                skips.append(f"h{prev_level} -> {h.name}")
            prev_level = level
        assert not skips, f"{path}: heading level skips: {skips}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_aria_roles_valid(self, path):
        """ARIA roles used should be valid."""
        valid_roles = {
            "alert", "alertdialog", "application", "article", "banner", "button",
            "cell", "checkbox", "columnheader", "combobox", "complementary",
            "contentinfo", "definition", "dialog", "directory", "document",
            "feed", "figure", "form", "grid", "gridcell", "group", "heading",
            "img", "link", "list", "listbox", "listitem", "log", "main",
            "marquee", "math", "menu", "menubar", "menuitem", "navigation",
            "none", "note", "option", "presentation", "progressbar", "radio",
            "radiogroup", "region", "row", "rowgroup", "rowheader", "scrollbar",
            "search", "searchbox", "separator", "slider", "spinbutton", "status",
            "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox",
            "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem",
        }
        soup = await fetch_page(path)
        elements_with_role = soup.select("[role]")
        invalid = [str(el) for el in elements_with_role if el.get("role") not in valid_roles]
        assert not invalid, f"{path}: invalid ARIA roles found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_live_regions_for_dynamic_content(self, path):
        """Dynamic content areas should have aria-live."""
        soup = await fetch_page(path)
        live_regions = soup.select("[aria-live], [role=alert], [role=status]")
        # Not all pages need live regions, but if they have dynamic content they should
        dynamic = soup.select("[data-dynamic], .dynamic, #notifications, .toast")
        if dynamic:
            assert live_regions, f"{path}: dynamic content without live region"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_duplicate_ids(self, path):
        """No duplicate IDs (breaks screen reader navigation)."""
        soup = await fetch_page(path)
        ids = [el.get("id") for el in soup.find_all(id=True)]
        duplicates = [i for i in set(ids) if ids.count(i) > 1]
        assert not duplicates, f"{path}: duplicate IDs: {duplicates}"


# ---------------------------------------------------------------------------
# 5. Focus Management
# ---------------------------------------------------------------------------

class TestFocusManagement:
    """Test focus management patterns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_focus_visible_styles(self, path):
        """CSS should define :focus-visible styles."""
        soup = await fetch_page(path)
        css_links = soup.select("link[rel=stylesheet]")
        found_focus_style = False
        for link in css_links:
            href = link.get("href", "")
            if href.startswith("http"):
                continue
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
                resp = await client.get(href)
                if ":focus" in resp.text or "focus-visible" in resp.text:
                    found_focus_style = True
                    break
        assert found_focus_style, f"{path}: no :focus styles found in CSS"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_modals_have_focus_trap(self, path):
        """Modal dialogs should have focus trap attributes."""
        soup = await fetch_page(path)
        modals = soup.select("[role=dialog], .modal, dialog")
        for modal in modals:
            assert modal.get("aria-modal") == "true" or modal.name == "dialog", \
                f"{path}: modal missing aria-modal=true"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_modals_have_labelledby(self, path):
        """Modal dialogs should reference their title via aria-labelledby."""
        soup = await fetch_page(path)
        modals = soup.select("[role=dialog], .modal, dialog")
        for modal in modals:
            assert modal.get("aria-labelledby") or modal.get("aria-label"), \
                f"{path}: modal missing aria-labelledby/aria-label"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_no_empty_links(self, path):
        """Links should not be empty (screen readers need text)."""
        soup = await fetch_page(path)
        links = soup.find_all("a", href=True)
        empty = [str(a) for a in links if not a.get_text(strip=True) and not a.get("aria-label")]
        assert not empty, f"{path}: {len(empty)} empty links found"
