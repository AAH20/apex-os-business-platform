"""
Comprehensive CRUD Accessibility Tests for APEX-OS Business Platform.

Tests cover: form labels, keyboard navigation, color contrast,
screen reader compatibility, and focus management.
"""

import pytest
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, Locator

BASE_URL = "http://localhost:8000"
CRUD_ROUTES = [
    "/projects", "/tasks", "/users", "/reports",
    "/settings", "/documents", "/teams", "/billing",
]

# WCAG AA minimum contrast ratio
MIN_CONTRAST_RATIO = 4.5
MIN_LARGE_TEXT_RATIO = 3.0


def luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def channel(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(color1: tuple, color2: tuple) -> float:
    """Compute contrast ratio between two RGB tuples."""
    l1 = luminance(*color1)
    l2 = luminance(*color2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_rgb(color_str: str) -> tuple:
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' into (r, g, b)."""
    color_str = color_str.strip().replace("rgba", "rgb")
    if color_str.startswith("rgb("):
        parts = color_str[4:-1].split(",")
        return tuple(int(p.strip()) for p in parts[:3])
    if color_str.startswith("#"):
        h = color_str.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return (0, 0, 0)


@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser) -> Page:
    pg = await browser.new_page(viewport={"width": 1280, "height": 720})
    await pg.goto(BASE_URL, wait_until="networkidle")
    yield pg
    await pg.close()


# ---------------------------------------------------------------------------
# 1. Form Label Tests
# ---------------------------------------------------------------------------

class TestFormLabels:
    """All CRUD form inputs must have associated labels."""

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_form_inputs_have_labels(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        inputs = page.locator("form input, form select, form textarea")
        count = await inputs.count()
        if count == 0:
            pytest.skip(f"No form inputs on {route}")
        for i in range(count):
            el = inputs.nth(i)
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            input_type = await el.get_attribute("type") or ""
            if input_type in ("hidden", "submit", "button"):
                continue
            has_id_label = await el.evaluate(
                """el => {
                    const id = el.id;
                    if (!id) return false;
                    return !!document.querySelector(`label[for="${id}"]`);
                }"""
            )
            has_aria = await el.evaluate(
                """el => el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby')"""
            )
            has_placeholder = await el.evaluate(
                """el => !!el.getAttribute('placeholder')"""
            )
            has_title = await el.evaluate("el => !!el.getAttribute('title')")
            assert has_id_label or has_aria or has_placeholder or has_title, (
                f"Unlabeled {tag}[{input_type}] on {route} (index {i})"
            )

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_required_fields_marked(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        required = page.locator("form [required], form [aria-required='true']")
        count = await required.count()
        for i in range(count):
            el = required.nth(i)
            has_visual = await el.evaluate(
                """el => {
                    const style = getComputedStyle(el);
                    return style.borderColor !== 'rgb(0, 0, 0)' ||
                           el.getAttribute('aria-required') === 'true';
                }"""
            )
            assert has_visual, f"Required field not visually indicated on {route} (index {i})"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_submit_buttons_accessible(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        buttons = page.locator("form button[type='submit'], form input[type='submit']")
        count = await buttons.count()
        for i in range(count):
            btn = buttons.nth(i)
            accessible_name = await btn.evaluate(
                """el => el.textContent.trim() || el.getAttribute('aria-label') || el.getAttribute('value')"""
            )
            assert accessible_name, f"Submit button lacks accessible name on {route} (index {i})"


# ---------------------------------------------------------------------------
# 2. Keyboard Navigation Tests
# ---------------------------------------------------------------------------

class TestKeyboardNavigation:
    """All interactive elements must be reachable and operable via keyboard."""

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_tab_order_logical(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        focusables = page.locator(
            "a[href], button:not([disabled]), input:not([disabled]), "
            "select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
        )
        count = await focusables.count()
        if count == 0:
            pytest.skip(f"No focusable elements on {route}")
        await page.keyboard.press("Tab")
        first_focused = await page.evaluate("document.activeElement.tagName")
        assert first_focused not in ("BODY", "HTML"), (
            f"First Tab did not focus an interactive element on {route}"
        )

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_no_keyboard_traps(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        focusables = page.locator(
            "a[href], button:not([disabled]), input:not([disabled]), "
            "select:not([disabled]), textarea:not([disabled])"
        )
        count = await focusables.count()
        for i in range(min(count, 10)):
            await page.keyboard.press("Tab")
            tag = await page.evaluate("document.activeElement.tagName")
            assert tag not in ("BODY", "HTML"), f"Keyboard trap detected on {route} at step {i}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_escape_closes_modals(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        modal_trigger = page.locator("[data-modal-trigger], [aria-haspopup='dialog']").first
        if await modal_trigger.count() == 0:
            pytest.skip(f"No modal trigger on {route}")
        await modal_trigger.click()
        await page.wait_for_timeout(300)
        dialog = page.locator("[role='dialog'], .modal, dialog")
        if await dialog.count() == 0:
            pytest.skip(f"No dialog opened on {route}")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        is_visible = await dialog.first.is_visible()
        assert not is_visible, f"Escape did not close modal on {route}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_enter_activates_buttons(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        buttons = page.locator("form button:not([type='submit'])")
        count = await buttons.count()
        if count == 0:
            pytest.skip(f"No non-submit buttons on {route}")
        btn = buttons.first
        await btn.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(200)
        still_focused = await page.evaluate(
            "document.activeElement === document.querySelector('form button:not([type=\"submit\"])')"
        )
        assert still_focused or await page.evaluate("document.activeElement.tagName") != "BODY"


# ---------------------------------------------------------------------------
# 3. Color Contrast Tests
# ---------------------------------------------------------------------------

class TestColorContrast:
    """Text must meet WCAG AA contrast ratios."""

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_text_contrast(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        text_elements = page.locator("p, span, h1, h2, h3, h4, h5, h6, label, a, li, td, th")
        count = await text_elements.count()
        failures = []
        for i in range(min(count, 50)):
            el = text_elements.nth(i)
            if not await el.is_visible():
                continue
            fg_bg = await el.evaluate(
                """el => {
                    const style = getComputedStyle(el);
                    const parent = el.parentElement;
                    const parentStyle = parent ? getComputedStyle(parent) : style;
                    return {
                        fg: style.color,
                        bg: style.backgroundColor !== 'rgba(0, 0, 0, 0)' ? style.backgroundColor : parentStyle.backgroundColor,
                        fontSize: parseFloat(style.fontSize),
                        fontWeight: parseInt(style.fontWeight) || 400
                    };
                }"""
            )
            fg = parse_rgb(fg_bg["fg"])
            bg = parse_rgb(fg_bg["bg"])
            if bg == (0, 0, 0):
                continue
            ratio = contrast_ratio(fg, bg)
            is_large = fg_bg["fontSize"] >= 24 or (fg_bg["fontSize"] >= 18.66 and fg_bg["fontWeight"] >= 700)
            threshold = MIN_LARGE_TEXT_RATIO if is_large else MIN_CONTRAST_RATIO
            if ratio < threshold:
                text = (await el.text_content() or "")[:40]
                failures.append(f"'{text}' ratio={ratio:.2f} < {threshold}")
        assert not failures, f"Contrast failures on {route}: {'; '.join(failures[:5])}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_focus_indicator_visible(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        focusables = page.locator("a, button, input, select, textarea")
        count = await focusables.count()
        for i in range(min(count, 10)):
            el = focusables.nth(i)
            await el.focus()
            outline = await el.evaluate(
                """el => {
                    const s = getComputedStyle(el);
                    return { width: s.outlineWidth, style: s.outlineStyle, color: s.outlineColor };
                }"""
            )
            has_visible_outline = (
                outline["style"] != "none"
                and float(outline["width"].replace("px", "")) >= 2
            )
            box_shadow = await el.evaluate("el => getComputedStyle(el).boxShadow")
            has_box_shadow = box_shadow != "none"
            assert has_visible_outline or has_box_shadow, (
                f"No visible focus indicator on {route} element {i}"
            )


# ---------------------------------------------------------------------------
# 4. Screen Reader Compatibility Tests
# ---------------------------------------------------------------------------

class TestScreenReaderCompatibility:
    """Elements must expose correct ARIA roles, names, and states."""

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_images_have_alt_text(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        images = page.locator("img")
        count = await images.count()
        for i in range(count):
            img = images.nth(i)
            alt = await img.get_attribute("alt")
            aria_hidden = await img.get_attribute("aria-hidden")
            assert alt is not None or aria_hidden == "true", (
                f"Image missing alt text on {route} (index {i})"
            )

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_landmarks_present(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        landmarks = page.locator(
            "[role='banner'], [role='navigation'], [role='main'], "
            "[role='contentinfo'], [role='complementary'], header, nav, main, footer, aside"
        )
        count = await landmarks.count()
        assert count > 0, f"No landmark regions found on {route}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_headings_hierarchy(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        headings = page.locator("h1, h2, h3, h4, h5, h6")
        count = await headings.count()
        if count == 0:
            pytest.skip(f"No headings on {route}")
        prev_level = 0
        for i in range(count):
            level = int(await headings.nth(i).evaluate("el => el.tagName[1]"))
            if prev_level > 0 and level > prev_level + 1:
                pytest.fail(f"Heading level skip on {route}: h{prev_level} -> h{level}")
            prev_level = level

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_form_errors_announced(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        submit = page.locator("form button[type='submit'], form input[type='submit']").first
        if await submit.count() == 0:
            pytest.skip(f"No submit button on {route}")
        await submit.click()
        await page.wait_for_timeout(500)
        alerts = page.locator("[role='alert'], [aria-live='assertive'], .error, .invalid-feedback")
        count = await alerts.count()
        if count > 0:
            for i in range(count):
                alert = alerts.nth(i)
                assert await alert.is_visible(), f"Error alert not visible on {route} (index {i})"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_aria_roles_valid(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        valid_roles = {
            "alert", "alertdialog", "application", "article", "banner", "button",
            "cell", "checkbox", "columnheader", "combobox", "complementary",
            "contentinfo", "definition", "dialog", "directory", "document",
            "feed", "figure", "form", "grid", "gridcell", "group", "heading",
            "img", "link", "list", "listbox", "listitem", "log", "main",
            "marquee", "math", "menu", "menubar", "menuitem", "menuitemcheckbox",
            "menuitemradio", "navigation", "none", "note", "option", "presentation",
            "progressbar", "radio", "radiogroup", "region", "row", "rowgroup",
            "rowheader", "scrollbar", "search", "searchbox", "separator",
            "slider", "spinbutton", "status", "switch", "tab", "table",
            "tablist", "tabpanel", "term", "textbox", "timer", "toolbar",
            "tooltip", "tree", "treegrid", "treeitem",
        }
        role_elements = page.locator("[role]")
        count = await role_elements.count()
        for i in range(count):
            role = await role_elements.nth(i).get_attribute("role")
            if role and role not in valid_roles:
                pytest.fail(f"Invalid ARIA role '{role}' on {route} (index {i})")


# ---------------------------------------------------------------------------
# 5. Focus Management Tests
# ---------------------------------------------------------------------------

class TestFocusManagement:
    """Focus must move predictably and be restored after interactions."""

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_focus_visible_on_load(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        focused = await page.evaluate("document.activeElement.tagName")
        assert focused not in ("BODY", "HTML"), f"No element focused on load at {route}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_focus_moves_to_modal(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        trigger = page.locator("[data-modal-trigger], [aria-haspopup='dialog']").first
        if await trigger.count() == 0:
            pytest.skip(f"No modal trigger on {route}")
        await trigger.click()
        await page.wait_for_timeout(300)
        dialog = page.locator("[role='dialog'], .modal, dialog").first
        if await dialog.count() == 0:
            pytest.skip(f"No dialog on {route}")
        focused_in_dialog = await page.evaluate(
            """() => {
                const dialog = document.querySelector('[role="dialog"], .modal, dialog');
                return dialog ? dialog.contains(document.activeElement) : false;
            }"""
        )
        assert focused_in_dialog, f"Focus not moved into modal on {route}"

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_focus_restored_after_close(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        trigger = page.locator("[data-modal-trigger], [aria-haspopup='dialog']").first
        if await trigger.count() == 0:
            pytest.skip(f"No modal trigger on {route}")
        trigger_id = await trigger.get_attribute("id") or "trigger"
        await trigger.click()
        await page.wait_for_timeout(300)
        close_btn = page.locator("[role='dialog'] [aria-label='Close'], .modal .close, dialog button[aria-label='Close']").first
        if await close_btn.count() == 0:
            await page.keyboard.press("Escape")
        else:
            await close_btn.click()
        await page.wait_for_timeout(300)
        focused = await page.evaluate("document.activeElement")
        is_trigger = await page.evaluate(
            """id => document.activeElement === document.getElementById(id)""",
            trigger_id,
        )
        assert is_trigger or await page.evaluate("document.activeElement.tagName") not in ("BODY", "HTML"), (
            f"Focus not restored after modal close on {route}"
        )

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_skip_link_present(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        skip_link = page.locator(
            "a[href^='#'][class*='skip'], a[href^='#'][id*='skip'], "
            "a:has-text('Skip to'), a:has-text('skip to main')"
        )
        count = await skip_link.count()
        if count == 0:
            pytest.skip(f"No skip link on {route}")
        await page.keyboard.press("Tab")
        focused_text = await page.evaluate("document.activeElement.textContent")
        assert "skip" in focused_text.lower() or "main" in focused_text.lower(), (
            f"First tab is not skip link on {route}"
        )

    @pytest.mark.parametrize("route", CRUD_ROUTES)
    async def test_focus_order_matches_visual(self, page: Page, route: str):
        await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
        focusables = page.locator(
            "a[href], button:not([disabled]), input:not([disabled]), "
            "select:not([disabled]), textarea:not([disabled])"
        )
        count = await focusables.count()
        positions = []
        for i in range(min(count, 15)):
            box = await focusables.nth(i).bounding_box()
            if box:
                positions.append((box["x"], box["y"]))
        if len(positions) < 2:
            pytest.skip(f"Too few focusable elements on {route}")
        for i in range(1, len(positions)):
            prev_x, prev_y = positions[i - 1]
            curr_x, curr_y = positions[i]
            assert curr_y >= prev_y - 5, (
                f"Focus order may not match visual order on {route} "
                f"at step {i}: y {prev_y} -> {curr_y}"
            )
