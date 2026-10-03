"""Comprehensive CRUD E2E tests for APEX-OS Business Platform."""
import pytest
import asyncio
from playwright.async_api import async_playwright, Page, expect

BASE_URL = "http://localhost:3000"

# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture(scope="session")
async def page(browser):
    ctx = await browser.new_context()
    page = await ctx.new_page()
    await page.goto(BASE_URL)
    yield page
    await ctx.close()

# ── 1. Page Load Tests ───────────────────────────────────────────────────

class TestPageLoads:
    """Verify all CRUD pages load without errors."""

    @pytest.mark.parametrize("path", [
        "/", "/dashboard", "/customers", "/products", "/orders",
        "/invoices", "/employees", "/suppliers", "/reports", "/settings",
    ])
    async def test_page_loads(self, page: Page, path: str):
        await page.goto(f"{BASE_URL}{path}")
        await page.wait_for_load_state("networkidle")
        assert page.url == f"{BASE_URL}{path}"
        assert await page.title() != ""
        # No error overlays
        error_el = page.locator(".error, .error-page, [role='alert']")
        assert await error_el.count() == 0

    async def test_no_console_errors(self, page: Page):
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        for path in ["/", "/customers", "/products", "/orders", "/invoices"]:
            await page.goto(f"{BASE_URL}{path}")
            await page.wait_for_load_state("networkidle")
        assert errors == [], f"Console errors: {errors}"

# ── 2. Form Submission Tests ─────────────────────────────────────────────

class TestFormSubmissions:
    """Verify all CRUD forms submit correctly."""

    async def test_create_customer(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/new")
        await page.fill("input[name='name']", "Test Customer")
        await page.fill("input[name='email']", "test@example.com")
        await page.fill("input[name='phone']", "555-0100")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "test@example.com" in await page.content()

    async def test_create_product(self, page: Page):
        await page.goto(f"{BASE_URL}/products/new")
        await page.fill("input[name='name']", "Test Product")
        await page.fill("input[name='price']", "29.99")
        await page.fill("input[name='sku']", "TEST-SKU-001")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "Test Product" in await page.content()

    async def test_create_order(self, page: Page):
        await page.goto(f"{BASE_URL}/orders/new")
        await page.select_option("select[name='customer']", index=1)
        await page.select_option("select[name='product']", index=1)
        await page.fill("input[name='quantity']", "2")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "order" in page.url.lower() or "success" in await page.content().lower()

    async def test_create_invoice(self, page: Page):
        await page.goto(f"{BASE_URL}/invoices/new")
        await page.fill("input[name='amount']", "150.00")
        await page.fill("input[name='due_date']", "2026-12-31")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "150" in await page.content()

    async def test_create_employee(self, page: Page):
        await page.goto(f"{BASE_URL}/employees/new")
        await page.fill("input[name='name']", "Jane Doe")
        await page.fill("input[name='email']", "jane@company.com")
        await page.fill("input[name='role']", "Engineer")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "Jane Doe" in await page.content()

    async def test_create_supplier(self, page: Page):
        await page.goto(f"{BASE_URL}/suppliers/new")
        await page.fill("input[name='name']", "Acme Supplies")
        await page.fill("input[name='contact']", "contact@acme.com")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "Acme Supplies" in await page.content()

    async def test_edit_customer(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        await page.locator("table tbody tr").first.locator("a.edit, button.edit").first.click()
        await page.wait_for_load_state("networkidle")
        await page.fill("input[name='name']", "Updated Customer")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "Updated Customer" in await page.content()

    async def test_delete_customer(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        count_before = await page.locator("table tbody tr").count()
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await page.locator("table tbody tr").first.locator("button.delete, a.delete").first.click()
        await page.wait_for_load_state("networkidle")
        count_after = await page.locator("table tbody tr").count()
        assert count_after < count_before

# ── 3. Button Tests ──────────────────────────────────────────────────────

class TestButtons:
    """Verify all buttons work correctly."""

    @pytest.mark.parametrize("path,selector", [
        ("/customers", "a:has-text('New Customer'), button:has-text('New Customer')"),
        ("/products", "a:has-text('New Product'), button:has-text('New Product')"),
        ("/orders", "a:has-text('New Order'), button:has-text('New Order')"),
        ("/invoices", "a:has-text('New Invoice'), button:has-text('New Invoice')"),
        ("/employees", "a:has-text('New Employee'), button:has-text('New Employee')"),
        ("/suppliers", "a:has-text('New Supplier'), button:has-text('New Supplier')"),
    ])
    async def test_new_button_navigates(self, page: Page, path: str, selector: str):
        await page.goto(f"{BASE_URL}{path}")
        await page.click(selector)
        await page.wait_for_load_state("networkidle")
        assert "new" in page.url.lower() or "create" in page.url.lower()

    async def test_save_button(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/new")
        await page.fill("input[name='name']", "Save Test")
        await page.click("button:has-text('Save'), button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "Save Test" in await page.content()

    async def test_cancel_button(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/new")
        await page.click("button:has-text('Cancel'), a:has-text('Cancel')")
        await page.wait_for_load_state("networkidle")
        assert "/customers" in page.url

    async def test_search_button(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        await page.fill("input[name='search'], input[type='search']", "test")
        await page.click("button:has-text('Search'), button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "test" in await page.content().lower()

    async def test_export_button(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        async with page.expect_download() as dl:
            await page.click("button:has-text('Export'), a:has-text('Export')")
        download = await dl.value
        assert download.suggested_filename

    async def test_pagination_buttons(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        next_btn = page.locator("button:has-text('Next'), a:has-text('Next')")
        if await next_btn.count() > 0:
            await next_btn.click()
            await page.wait_for_load_state("networkidle")
            assert "page=2" in page.url or "2" in await page.content()

# ── 4. Link Tests ────────────────────────────────────────────────────────

class TestLinks:
    """Verify all links work correctly."""

    @pytest.mark.parametrize("path,link_text,expected_url", [
        ("/dashboard", "Customers", "/customers"),
        ("/dashboard", "Products", "/products"),
        ("/dashboard", "Orders", "/orders"),
        ("/dashboard", "Invoices", "/invoices"),
        ("/dashboard", "Employees", "/employees"),
        ("/dashboard", "Suppliers", "/suppliers"),
        ("/dashboard", "Reports", "/reports"),
        ("/dashboard", "Settings", "/settings"),
    ])
    async def test_nav_links(self, page: Page, path: str, link_text: str, expected_url: str):
        await page.goto(f"{BASE_URL}{path}")
        await page.click(f"a:has-text('{link_text}')")
        await page.wait_for_load_state("networkidle")
        assert expected_url in page.url

    async def test_breadcrumb_links(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/1")
        breadcrumbs = page.locator(".breadcrumb a, nav a")
        count = await breadcrumbs.count()
        assert count > 0
        await breadcrumbs.first.click()
        await page.wait_for_load_state("networkidle")
        assert page.url != f"{BASE_URL}/customers/1"

    async def test_table_row_links(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        row_link = page.locator("table tbody tr td a").first
        if await row_link.count() > 0:
            await row_link.click()
            await page.wait_for_load_state("networkidle")
            assert "customer" in page.url.lower()

    async def test_logo_link(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        await page.click(".logo a, header a[href='/']")
        await page.wait_for_load_state("networkidle")
        assert page.url.rstrip("/").endswith(":3000")

# ── 5. Dropdown Tests ────────────────────────────────────────────────────

class TestDropdowns:
    """Verify all dropdowns work correctly."""

    async def test_customer_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/orders/new")
        select = page.locator("select[name='customer']")
        count = await select.locator("option").count()
        assert count > 1
        await select.select_option(index=1)
        val = await select.input_value()
        assert val != ""

    async def test_product_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/orders/new")
        select = page.locator("select[name='product']")
        count = await select.locator("option").count()
        assert count > 1
        await select.select_option(index=1)
        val = await select.input_value()
        assert val != ""

    async def test_status_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/orders")
        select = page.locator("select[name='status'], select[name='filter']")
        if await select.count() > 0:
            await select.select_option(index=1)
            await page.wait_for_load_state("networkidle")
            val = await select.input_value()
            assert val != ""

    async def test_role_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/employees/new")
        select = page.locator("select[name='role'], select[name='department']")
        if await select.count() > 0:
            await select.select_option(index=1)
            val = await select.input_value()
            assert val != ""

    async def test_sort_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/customers")
        select = page.locator("select[name='sort'], select[name='order_by']")
        if await select.count() > 0:
            await select.select_option(index=1)
            await page.wait_for_load_state("networkidle")
            val = await select.input_value()
            assert val != ""

    async def test_currency_dropdown(self, page: Page):
        await page.goto(f"{BASE_URL}/settings")
        select = page.locator("select[name='currency'], select[name='language']")
        if await select.count() > 0:
            await select.select_option(index=1)
            val = await select.input_value()
            assert val != ""

# ── 6. Validation Tests ──────────────────────────────────────────────────

class TestFormValidation:
    """Verify form validation works correctly."""

    async def test_required_field_validation(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/new")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(500)
        # Should stay on form or show error
        assert "new" in page.url.lower() or "create" in page.url.lower()
        error = page.locator(".error, .invalid-feedback, [role='alert']")
        assert await error.count() > 0

    async def test_email_validation(self, page: Page):
        await page.goto(f"{BASE_URL}/customers/new")
        await page.fill("input[name='name']", "Test")
        await page.fill("input[name='email']", "not-an-email")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(500)
        assert "new" in page.url.lower() or "create" in page.url.lower()

# ── 7. Auth Tests ────────────────────────────────────────────────────────

class TestAuth:
    """Verify auth flows work correctly."""

    async def test_login_page_loads(self, page: Page):
        await page.goto(f"{BASE_URL}/login")
        await page.wait_for_load_state("networkidle")
        assert page.url == f"{BASE_URL}/login"

    async def test_login_form(self, page: Page):
        await page.goto(f"{BASE_URL}/login")
        await page.fill("input[name='email']", "admin@example.com")
        await page.fill("input[name='password']", "password123")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        assert "/login" not in page.url

    async def test_logout(self, page: Page):
        await page.goto(f"{BASE_URL}/dashboard")
        logout = page.locator("button:has-text('Logout'), a:has-text('Logout')")
        if await logout.count() > 0:
            await logout.click()
            await page.wait_for_load_state("networkidle")
            assert "/login" in page.url or "/" == page.url.split(BASE_URL)[1]

# ── 8. Dashboard Widget Tests ────────────────────────────────────────────

class TestDashboardWidgets:
    """Verify dashboard widgets render correctly."""

    async def test_stats_cards(self, page: Page):
        await page.goto(f"{BASE_URL}/dashboard")
        cards = page.locator(".stat-card, .metric-card, .dashboard-card")
        assert await cards.count() > 0

    async def test_recent_activity(self, page: Page):
        await page.goto(f"{BASE_URL}/dashboard")
        activity = page.locator(".recent-activity, .activity-feed, .timeline")
        assert await activity.count() > 0

    async def test_chart_renders(self, page: Page):
        await page.goto(f"{BASE_URL}/dashboard")
        chart = page.locator("canvas, .chart, svg.chart")
        assert await chart.count() > 0
