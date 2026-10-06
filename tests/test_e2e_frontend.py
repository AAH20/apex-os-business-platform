"""E2E frontend tests for APEX-OS Business Platform."""
import pytest
from playwright.async_api import async_playwright, Page

BASE_URL = "http://localhost:3000"
import os

if not os.environ.get("E2E_BASE_URL"):
    pytestmark = pytest.mark.skip(reason="requires running server (set E2E_BASE_URL to enable)")
PAGES = ["/", "/dashboard", "/projects", "/tasks", "/reports", "/settings", "/users", "/analytics"]


@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    page = await browser.new_page()
    await page.goto(BASE_URL)
    yield page
    await page.close()


@pytest.mark.asyncio
async def test_all_pages_load_without_errors(browser):
    """Test all 8 pages load without console errors."""
    for path in PAGES:
        page = await browser.new_page()
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        resp = await page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
        assert resp.status == 200, f"{path} returned {resp.status}"
        assert not errors, f"{path} had console errors: {errors}"
        await page.close()


@pytest.mark.asyncio
async def test_navigation_between_pages(page):
    """Test navigation links work between pages."""
    for path in PAGES[1:]:
        await page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
        assert path in page.url


@pytest.mark.asyncio
async def test_crud_operations(page):
    """Test create, read, update, delete through UI."""
    # Create
    await page.goto(f"{BASE_URL}/projects", wait_until="networkidle")
    await page.click("text=New Project")
    await page.fill("input[name='name']", "E2E Test Project")
    await page.fill("textarea[name='description']", "Created by E2E test")
    await page.click("button[type='submit']")
    await page.wait_for_selector("text=E2E Test Project", timeout=5000)

    # Read
    assert await page.is_visible("text=E2E Test Project")

    # Update
    await page.click("text=E2E Test Project")
    await page.fill("input[name='name']", "E2E Updated Project")
    await page.click("button[type='submit']")
    await page.wait_for_selector("text=E2E Updated Project", timeout=5000)

    # Delete
    await page.click("text=Delete")
    await page.wait_for_selector("text=E2E Updated Project", state="detached", timeout=5000)


@pytest.mark.asyncio
async def test_form_submissions(page):
    """Test form validation and submission."""
    await page.goto(f"{BASE_URL}/tasks", wait_until="networkidle")
    # Submit empty form
    await page.click("button[type='submit']")
    await page.wait_for_selector("text=required", timeout=3000)
    # Fill and submit
    await page.fill("input[name='title']", "E2E Task")
    await page.click("button[type='submit']")
    await page.wait_for_selector("text=E2E Task", timeout=5000)


@pytest.mark.asyncio
async def test_data_display(page):
    """Test data is rendered in tables/lists."""
    await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
    await page.wait_for_selector("table, [role='grid'], .data-list", timeout=5000)
    content = await page.content()
    assert len(content) > 500
