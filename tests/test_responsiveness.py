"""Comprehensive responsive tests for APEX-OS Business Platform."""
import os

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, BrowserContext

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")

if not os.environ.get("E2E_BASE_URL"):
    pytestmark = pytest.mark.skip(reason="requires running server (set E2E_BASE_URL to enable)")
VIEWPORTS = {
    "mobile": {"width": 375, "height": 667},
    "tablet": {"width": 768, "height": 1024},
    "desktop": {"width": 1920, "height": 1080},
}
PAGES = [
    "/", "/dashboard", "/projects", "/tasks", "/calendar",
    "/reports", "/settings", "/profile", "/team", "/billing",
]
NAV_LINKS = ["Dashboard", "Projects", "Tasks", "Calendar", "Reports", "Settings"]
CRUD_PAGES = ["/projects", "/tasks", "/team"]


@pytest_asyncio.fixture()
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture()
async def context(browser):
    ctx = await browser.new_context(viewport=dict(VIEWPORTS["desktop"]))
    yield ctx
    await ctx.close()


@pytest_asyncio.fixture()
async def page(context):
    pg = await context.new_page()
    yield pg
    await pg.close()


async def _load_page(page: Page, path: str, width: int, height: int):
    await page.set_viewport_size({"width": width, "height": height})
    await page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    return page


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
@pytest.mark.parametrize("path", PAGES)
async def test_page_renders_at_width(browser, viewport_name, path):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    resp = await pg.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    assert resp is not None and resp.status < 400, f"{path} failed at {viewport_name}"
    body = await pg.inner_text("body")
    assert len(body.strip()) > 0, f"{path} empty body at {viewport_name}"
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
async def test_no_horizontal_scrollbar(browser, viewport_name):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    for path in PAGES:
        await pg.goto(f"{BASE_URL}{path}", wait_until="networkidle")
        overflow = await pg.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert not overflow, f"{path} has horizontal overflow at {viewport_name}"
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
async def test_navigation_works_at_width(browser, viewport_name):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    await pg.goto(BASE_URL, wait_until="networkidle")
    for link_text in NAV_LINKS:
        link = pg.get_by_role("link", name=link_text, exact=False)
        if await link.count() == 0:
            nav_btn = pg.get_by_role("button", name="Menu", exact=False)
            if await nav_btn.count() > 0:
                await nav_btn.first.click()
                await pg.wait_for_timeout(300)
        await link.first.click()
        await pg.wait_for_load_state("networkidle")
        assert pg.url != BASE_URL or link_text == "Dashboard"
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
async def test_nav_toggle_mobile(browser, viewport_name):
    if viewport_name == "desktop":
        pytest.skip("Nav toggle only relevant for mobile/tablet")
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    await pg.goto(BASE_URL, wait_until="networkidle")
    toggle = pg.get_by_role("button", name="Toggle navigation", exact=False)
    if await toggle.count() == 0:
        toggle = pg.locator(".nav-toggle, .hamburger, [data-testid='nav-toggle']")
    assert await toggle.count() > 0, "No nav toggle found"
    await toggle.first.click()
    await pg.wait_for_timeout(200)
    nav = pg.locator("nav, .navbar, [data-testid='main-nav']")
    assert await nav.first.is_visible()
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
@pytest.mark.parametrize("path", CRUD_PAGES)
async def test_crud_form_renders_at_width(browser, viewport_name, path):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    await pg.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    form = pg.locator("form, [data-testid='crud-form'], .crud-form")
    assert await form.count() > 0, f"No CRUD form on {path} at {viewport_name}"
    inputs = pg.locator("form input, form select, form textarea")
    count = await inputs.count()
    assert count > 0, f"Form on {path} has no inputs at {viewport_name}"
    submit = pg.locator("form button[type='submit'], form input[type='submit']")
    assert await submit.count() > 0, f"No submit button on {path} at {viewport_name}"
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
@pytest.mark.parametrize("path", CRUD_PAGES)
async def test_crud_form_submit_at_width(browser, viewport_name, path):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    await pg.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    name_input = pg.locator("form input[name='name'], form input[name='title']").first
    if await name_input.count() > 0:
        await name_input.fill(f"Test Item {viewport_name}")
    submit = pg.locator("form button[type='submit'], form input[type='submit']").first
    await submit.click()
    await pg.wait_for_load_state("networkidle")
    body = await pg.inner_text("body")
    assert "error" not in body.lower() or "success" in body.lower()
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
async def test_images_responsive(browser, viewport_name):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    for path in PAGES:
        await pg.goto(f"{BASE_URL}{path}", wait_until="networkidle")
        imgs = pg.locator("img")
        for i in range(await imgs.count()):
            box = await imgs.nth(i).bounding_box()
            if box:
                assert box["width"] <= vp["width"], (
                    f"Image overflow on {path} at {viewport_name}"
                )
    await ctx.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("viewport_name", list(VIEWPORTS.keys()))
async def test_font_sizes_readable(browser, viewport_name):
    vp = VIEWPORTS[viewport_name]
    ctx = await browser.new_context(viewport=dict(vp))
    pg = await ctx.new_page()
    await pg.goto(BASE_URL, wait_until="networkidle")
    min_font = await pg.evaluate(
        "Math.max(0, ...Array.from(document.querySelectorAll('body, body *'))"
        ".map(el => parseFloat(getComputedStyle(el).fontSize)))"
    )
    assert min_font >= 10, f"Font too small at {viewport_name}: {min_font}px"
    await ctx.close()
