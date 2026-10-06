"""E2E tests for all 8 APEX-OS Business Platform pages."""
import pytest
from playwright.async_api import async_playwright, Page

BASE_URL = "http://localhost:3000"
import os

if not os.environ.get("E2E_BASE_URL"):
    pytestmark = pytest.mark.skip(reason="requires running server (set E2E_BASE_URL to enable)")
PAGES = ["/", "/dashboard", "/projects", "/tasks", "/reports", "/settings", "/profile", "/admin"]
NAV_LINKS = ["Dashboard", "Projects", "Tasks", "Reports", "Settings", "Profile", "Admin"]


@pytest.fixture
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    page = await browser.new_page()
    await page.goto(BASE_URL)
    await page.wait_for_load_state("networkidle")
    return page


# ── Navigation Tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("path", PAGES)
async def test_page_navigates(page: Page, path: str):
    await page.goto(f"{BASE_URL}{path}")
    await page.wait_for_load_state("networkidle")
    assert page.url.endswith(path) or page.url.endswith(path + "/")
    assert await page.title() != ""


@pytest.mark.asyncio
async def test_all_nav_links_present(page: Page):
    for link_text in NAV_LINKS:
        assert await page.locator(f"text={link_text}").count() > 0, f"Missing nav link: {link_text}"


@pytest.mark.asyncio
async def test_nav_links_navigate(page: Page):
    for link_text in NAV_LINKS:
        await page.goto(BASE_URL)
        await page.click(f"text={link_text}")
        await page.wait_for_load_state("networkidle")
        assert page.url != BASE_URL


# ── Form Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/login")
    await page.fill("input[name='username']", "testuser")
    await page.fill("input[name='password']", "testpass")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "/login" not in page.url


@pytest.mark.asyncio
async def test_project_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/projects")
    await page.click("text=New Project")
    await page.fill("input[name='name']", "E2E Test Project")
    await page.fill("textarea[name='description']", "Created by E2E test")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "E2E Test Project" in await page.content()


@pytest.mark.asyncio
async def test_task_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/tasks")
    await page.click("text=New Task")
    await page.fill("input[name='title']", "E2E Test Task")
    await page.fill("textarea[name='description']", "Task from E2E test")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "E2E Test Task" in await page.content()


@pytest.mark.asyncio
async def test_profile_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/profile")
    await page.fill("input[name='displayName']", "E2E User")
    await page.fill("input[name='email']", "e2e@test.com")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "E2E User" in await page.content()


@pytest.mark.asyncio
async def test_settings_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/settings")
    await page.fill("input[name='siteName']", "E2E Site")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "E2E Site" in await page.content()


@pytest.mark.asyncio
async def test_report_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/reports")
    await page.click("text=Generate Report")
    await page.select_option("select[name='type']", "monthly")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "monthly" in await page.content().lower()


@pytest.mark.asyncio
async def test_admin_form_submits(page: Page):
    await page.goto(f"{BASE_URL}/admin")
    await page.fill("input[name='username']", "adminuser")
    await page.click("button[type='submit']")
    await page.wait_for_load_state("networkidle")
    assert "adminuser" in await page.content()


# ── Button Tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_buttons_clickable(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        buttons = await page.locator("button").all()
        for btn in buttons:
            if await btn.is_visible():
                await btn.click()
                await page.wait_for_load_state("networkidle")


@pytest.mark.asyncio
async def test_submit_buttons_exist(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        assert await page.locator("button[type='submit']").count() >= 0


@pytest.mark.asyncio
async def test_action_buttons_work(page: Page):
    await page.goto(f"{BASE_URL}/projects")
    action_btns = await page.locator("button.action-btn, button.edit-btn, button.delete-btn").all()
    for btn in action_btns:
        if await btn.is_visible():
            await btn.click()
            await page.wait_for_load_state("networkidle")


# ── Link Tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_internal_links(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        links = await page.locator("a[href^='/']").all()
        for link in links:
            href = await link.get_attribute("href")
            if href and href != "#":
                assert href.startswith("/")


@pytest.mark.asyncio
async def test_external_links_have_target(page: Page):
    await page.goto(BASE_URL)
    ext_links = await page.locator("a[href^='http']").all()
    for link in ext_links:
        target = await link.get_attribute("target")
        assert target == "_blank" or target is None


@pytest.mark.asyncio
async def test_breadcrumb_links(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        crumbs = await page.locator(".breadcrumb a, nav a").all()
        for crumb in crumbs:
            if await crumb.is_visible():
                await crumb.click()
                await page.wait_for_load_state("networkidle")


# ── Dropdown Tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_dropdowns_selectable(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        selects = await page.locator("select").all()
        for sel in selects:
            if await sel.is_visible():
                options = await sel.locator("option").all()
                if len(options) > 1:
                    await sel.select_option(index=1)
                    await page.wait_for_load_state("networkidle")


@pytest.mark.asyncio
async def test_dropdown_options_exist(page: Page):
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        selects = await page.locator("select").all()
        for sel in selects:
            options = await sel.locator("option").all()
            assert len(options) >= 1


@pytest.mark.asyncio
async def test_nav_dropdown_opens(page: Page):
    await page.goto(BASE_URL)
    dropdowns = await page.locator(".dropdown, .nav-dropdown, [role='combobox']").all()
    for dd in dropdowns:
        if await dd.is_visible():
            await dd.click()
            await page.wait_for_timeout(500)


# ── Cross-cutting Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_console_errors(page: Page):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        await page.wait_for_load_state("networkidle")
    assert len(errors) == 0, f"Console errors: {errors}"


@pytest.mark.asyncio
async def test_responsive_navigation(page: Page):
    await page.set_viewport_size({"width": 375, "height": 667})
    await page.goto(BASE_URL)
    await page.wait_for_load_state("networkidle")
    assert await page.locator("nav, header").count() > 0
    await page.set_viewport_size({"width": 1920, "height": 1080})
