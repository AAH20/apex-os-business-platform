"""Comprehensive accessibility tests for all APEX-OS Business Platform pages."""
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page

BASE_URL = "http://localhost:3000"
PAGES = [
    "/", "/dashboard", "/projects", "/tasks", "/calendar",
    "/reports", "/settings", "/profile", "/team", "/billing",
]

# WCAG AA minimum contrast ratio
MIN_CONTRAST_RATIO = 4.5


async def get_element_contrast(page: Page, selector: str) -> float:
    """Calculate contrast ratio between foreground and background colors."""
    return await page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return 0;
            const style = getComputedStyle(el);
            const fg = style.color;
            const bg = style.backgroundColor;
            const parse = (c) => {
                const m = c.match(/\\d+/g);
                return m ? m.slice(0, 3).map(Number) : [0, 0, 0];
            };
            const lum = ([r, g, b]) => {
                const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
                return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
            };
            const [fr, fg_, fb] = parse(fg);
            const [br, bg_, bb] = parse(bg);
            const l1 = lum([fr, fg_, fb]);
            const l2 = lum([br, bg_, bb]);
            const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
            return (hi + 0.05) / (lo + 0.05);
        }""",
        selector,
    )


@pytest_asyncio.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser):
    page = await browser.new_page()
    yield page
    await page.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_has_title(page: Page, path):
    """Every page must have a non-empty document title."""
    await page.goto(f"{BASE_URL}{path}")
    title = await page.title()
    assert title and len(title.strip()) > 0, f"Page {path} missing title"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_has_main_landmark(page: Page, path):
    """Every page must have a main landmark region."""
    await page.goto(f"{BASE_URL}{path}")
    main = page.locator("main, [role='main']")
    assert await main.count() >= 1, f"Page {path} missing main landmark"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_has_h1(page: Page, path):
    """Every page must have exactly one h1 heading."""
    await page.goto(f"{BASE_URL}{path}")
    h1_count = await page.locator("h1").count()
    assert h1_count == 1, f"Page {path} has {h1_count} h1 elements (expected 1)"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_images_have_alt_text(page: Page, path):
    """All images must have alt attributes."""
    await page.goto(f"{BASE_URL}{path}")
    images = page.locator("img:not([alt])")
    count = await images.count()
    assert count == 0, f"Page {path} has {count} images without alt text"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_buttons_have_accessible_names(page: Page, path):
    """All buttons must have accessible names (text or aria-label)."""
    await page.goto(f"{BASE_URL}{path}")
    unnamed = page.locator("button:not([aria-label]):not([aria-labelledby]):not(:has-text(''))")
    count = await unnamed.count()
    assert count == 0, f"Page {path} has {count} buttons without accessible names"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_form_inputs_have_labels(page: Page, path):
    """All form inputs must have associated labels."""
    await page.goto(f"{BASE_URL}{path}")
    inputs = page.locator("input:not([type='hidden']):not([aria-label]):not([aria-labelledby])")
    total = await inputs.count()
    unlabeled = 0
    for i in range(total):
        input_el = inputs.nth(i)
        input_id = await input_el.get_attribute("id")
        input_type = await input_el.get_attribute("type")
        if input_type in ("submit", "button", "reset"):
            continue
        if input_id:
            label = page.locator(f"label[for='{input_id}']")
            if await label.count() == 0:
                unlabeled += 1
        else:
            unlabeled += 1
    assert unlabeled == 0, f"Page {path} has {unlabeled} unlabeled form inputs"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_keyboard_navigation_links(page: Page, path):
    """All interactive elements must be reachable via keyboard (Tab)."""
    await page.goto(f"{BASE_URL}{path}")
    await page.keyboard.press("Tab")
    focused = await page.evaluate("document.activeElement.tagName")
    assert focused not in ("BODY", "HTML"), f"Page {path}: first Tab did not focus an element"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_focus_visible_on_interactive_elements(page: Page, path):
    """Interactive elements must have visible focus indicators."""
    await page.goto(f"{BASE_URL}{path}")
    links = page.locator("a[href]")
    count = await links.count()
    if count == 0:
        pytest.skip(f"Page {path} has no links")
    first_link = links.first
    await first_link.focus()
    outline = await first_link.evaluate(
        "el => { const s = getComputedStyle(el); return s.outlineStyle + ' ' + s.outlineWidth; }"
    )
    assert "none" not in outline or "0px" not in outline, (
        f"Page {path}: focused element has no visible focus indicator"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_color_contrast_text(page: Page, path):
    """Text elements must meet WCAG AA contrast ratio (4.5:1)."""
    await page.goto(f"{BASE_URL}{path}")
    selectors = ["p", "span", "a", "button", "h1", "h2", "h3", "label", "li"]
    failures = []
    for sel in selectors:
        elements = page.locator(sel)
        count = await elements.count()
        for i in range(min(count, 10)):
            el = elements.nth(i)
            visible = await el.is_visible()
            if not visible:
                continue
            ratio = await get_element_contrast(page, f"{sel}:nth-of-type({i + 1})")
            if 0 < ratio < MIN_CONTRAST_RATIO:
                failures.append(f"{sel}:nth-of-type({i + 1}) ratio={ratio:.2f}")
    assert len(failures) == 0, f"Page {path} contrast failures: {failures[:5]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_aria_roles_present(page: Page, path):
    """Pages must use appropriate ARIA roles for key UI components."""
    await page.goto(f"{BASE_URL}{path}")
    nav = page.locator("nav, [role='navigation']")
    assert await nav.count() >= 1, f"Page {path} missing navigation landmark"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_heading_hierarchy(page: Page, path):
    """Headings must not skip levels (h1 -> h3 is invalid)."""
    await page.goto(f"{BASE_URL}{path}")
    headings = page.locator("h1, h2, h3, h4, h5, h6")
    count = await headings.count()
    prev_level = 0
    for i in range(count):
        level = int(await headings.nth(i).evaluate("el => el.tagName[1]"))
        if prev_level > 0 and level > prev_level + 1:
            pytest.fail(f"Page {path}: heading level skip from h{prev_level} to h{level}")
        prev_level = level


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_screen_reader_live_regions(page: Page, path):
    """Dynamic content areas should have aria-live where appropriate."""
    await page.goto(f"{BASE_URL}{path}")
    live_regions = page.locator("[aria-live], [role='status'], [role='alert']")
    count = await live_regions.count()
    # Not all pages need live regions, but if they have dynamic content they should
    dynamic = page.locator("[data-dynamic], .toast, .notification, .alert")
    dynamic_count = await dynamic.count()
    if dynamic_count > 0:
        assert count >= 1, f"Page {path} has dynamic content but no live regions"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_focus_management_dialog(page: Page, path):
    """If a dialog exists, focus should be trapped within it."""
    await page.goto(f"{BASE_URL}{path}")
    dialog = page.locator("[role='dialog'], dialog")
    if await dialog.count() == 0:
        pytest.skip(f"Page {path} has no dialog")
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(200)
    focused_in_dialog = await page.evaluate(
        """() => {
            const dlg = document.querySelector('[role="dialog"], dialog');
            return dlg ? dlg.contains(document.activeElement) : false;
        }"""
    )
    # After Escape, focus should leave dialog or dialog should close
    dialog_visible = await dialog.first.is_visible()
    assert not dialog_visible or focused_in_dialog, (
        f"Page {path}: focus not properly managed in dialog"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_skip_navigation_link(page: Page, path):
    """Pages should have a skip navigation link for keyboard users."""
    await page.goto(f"{BASE_URL}{path}")
    skip_link = page.locator("a[href^='#main'], a[href^='#content'], .skip-link, .skip-nav")
    assert await skip_link.count() >= 1, f"Page {path} missing skip navigation link"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_language_attribute(page: Page, path):
    """HTML element must have a lang attribute for screen readers."""
    await page.goto(f"{BASE_URL}{path}")
    lang = await page.evaluate("document.documentElement.lang")
    assert lang and len(lang) >= 2, f"Page {path}: html lang attribute missing or invalid"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_no_empty_links_or_buttons(page: Page, path):
    """Links and buttons must not be empty (no accessible name)."""
    await page.goto(f"{BASE_URL}{path}")
    empty_links = page.locator("a[href]:not(:has-text('')):not(:has(svg)):not(:has(img))")
    empty_buttons = page.locator("button:not(:has-text('')):not(:has(svg)):not(:has(img))")
    link_count = await empty_links.count()
    btn_count = await empty_buttons.count()
    assert link_count == 0, f"Page {path} has {link_count} empty links"
    assert btn_count == 0, f"Page {path} has {btn_count} empty buttons"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_form_error_announcements(page: Page, path):
    """Form errors should be announced via aria-describedby or aria-live."""
    await page.goto(f"{BASE_URL}{path}")
    error_elements = page.locator(".error, .invalid, [aria-invalid='true']")
    count = await error_elements.count()
    for i in range(count):
        el = error_elements.nth(i)
        describedby = await el.get_attribute("aria-describedby")
        live = await el.get_attribute("aria-live")
        assert describedby or live, (
            f"Page {path}: error element {i} not announced to screen readers"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_table_headers_present(page: Page, path):
    """Data tables must have proper header cells."""
    await page.goto(f"{BASE_URL}{path}")
    tables = page.locator("table")
    count = await tables.count()
    for i in range(count):
        table = tables.nth(i)
        headers = table.locator("th")
        assert await headers.count() >= 1, f"Page {path}: table {i} missing header cells"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_zoom_compatibility(page: Page, path):
    """Pages should remain functional at 200% zoom."""
    await page.goto(f"{BASE_URL}{path}")
    await page.evaluate("document.body.style.zoom = '200%'")
    await page.wait_for_timeout(300)
    overflow = await page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow, f"Page {path}: horizontal overflow at 200% zoom"
    await page.evaluate("document.body.style.zoom = '100%'")
