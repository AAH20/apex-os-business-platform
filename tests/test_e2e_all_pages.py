"""E2E tests for all 8 pages of APEX-OS Business Platform."""
import pytest
from playwright.async_api import async_playwright, Page, expect

BASE_URL = "http://localhost:3000"
import os

if not os.environ.get("E2E_BASE_URL"):
    pytestmark = pytest.mark.skip(reason="requires running server (set E2E_BASE_URL to enable)")
PAGES = ["/", "/users", "/products", "/orders", "/reports", "/analytics", "/settings", "/profile"]
NAV_LINKS = ["Dashboard", "Users", "Products", "Orders", "Reports", "Analytics", "Settings", "Profile"]


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
    return page


@pytest.mark.asyncio
async def test_all_pages_load_without_errors(page):
    """Test all 8 pages load without console errors."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    for path in PAGES:
        await page.goto(f"{BASE_URL}{path}")
        await page.wait_for_load_state("networkidle")
        assert page.url.endswith(path), f"URL mismatch for {path}"
    assert not errors, f"Console errors: {errors}"


@pytest.mark.asyncio
async def test_navigation_between_pages(page):
    """Test navigation between all pages via nav links."""
    for link_text in NAV_LINKS:
        await page.click(f"nav >> text={link_text}")
        await page.wait_for_load_state("networkidle")
        assert link_text.lower() in page.url.lower(), f"Navigation to {link_text} failed"


@pytest.mark.asyncio
async def test_users_crud_operations(page):
    """Test CRUD operations on Users page."""
    await page.goto(f"{BASE_URL}/users")
    await page.click("text=Add User")
    await page.fill("input[name='name']", "Test User")
    await page.fill("input[name='email']", "test@example.com")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Test User")).to_be_visible()
    await page.click("text=Test User >> xpath=.. >> text=Edit")
    await page.fill("input[name='name']", "Updated User")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Updated User")).to_be_visible()
    await page.click("text=Updated User >> xpath=.. >> text=Delete")
    await page.click("text=Confirm")
    await expect(page.locator("text=Updated User")).not_to_be_visible()


@pytest.mark.asyncio
async def test_products_crud_operations(page):
    """Test CRUD operations on Products page."""
    await page.goto(f"{BASE_URL}/products")
    await page.click("text=Add Product")
    await page.fill("input[name='name']", "Test Product")
    await page.fill("input[name='price']", "99.99")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Test Product")).to_be_visible()
    await page.click("text=Test Product >> xpath=.. >> text=Edit")
    await page.fill("input[name='price']", "149.99")
    await page.click("button[type='submit']")
    await expect(page.locator("text=149.99")).to_be_visible()
    await page.click("text=Test Product >> xpath=.. >> text=Delete")
    await page.click("text=Confirm")
    await expect(page.locator("text=Test Product")).not_to_be_visible()


@pytest.mark.asyncio
async def test_orders_crud_operations(page):
    """Test CRUD operations on Orders page."""
    await page.goto(f"{BASE_URL}/orders")
    await page.click("text=New Order")
    await page.select_option("select[name='product']", index=1)
    await page.fill("input[name='quantity']", "5")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Order #")).to_be_visible()
    await page.click("text=Pending >> xpath=.. >> text=Cancel")
    await page.click("text=Confirm")
    await expect(page.locator("text=Cancelled")).to_be_visible()


@pytest.mark.asyncio
async def test_form_submissions(page):
    """Test form submissions on Settings and Profile pages."""
    await page.goto(f"{BASE_URL}/settings")
    await page.fill("input[name='site_name']", "APEX-OS Test")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Settings saved")).to_be_visible()
    await page.goto(f"{BASE_URL}/profile")
    await page.fill("input[name='fullName']", "Test Admin")
    await page.fill("input[name='email']", "admin@test.com")
    await page.click("button[type='submit']")
    await expect(page.locator("text=Profile updated")).to_be_visible()


@pytest.mark.asyncio
async def test_data_display(page):
    """Test data display on Dashboard, Reports, and Analytics pages."""
    await page.goto(BASE_URL)
    await expect(page.locator(".stats-card")).to_have_count(4)
    await expect(page.locator("table")).to_be_visible()
    await page.goto(f"{BASE_URL}/reports")
    await expect(page.locator("table")).to_be_visible()
    await expect(page.locator("tbody tr")).to_have_count(5)
    await page.goto(f"{BASE_URL}/analytics")
    await expect(page.locator(".chart")).to_be_visible()
    await expect(page.locator(".metric")).to_have_count(3)
