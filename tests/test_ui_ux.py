"""Comprehensive UI/UX tests for APEX-OS Business Platform."""
import re
import httpx
import pytest
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"
PAGES = ["/", "/dashboard", "/analytics", "/crm", "/projects", "/tasks",
         "/inventory", "/orders", "/invoices", "/payments", "/employees",
         "/customers", "/products", "/notifications", "/settings"]

async def fetch_page(path: str) -> tuple[int, str]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get(path)
        return resp.status_code, resp.text

def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

class TestContrastRatios:
    """Test all pages have proper contrast ratios (WCAG AA: 4.5:1)."""
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_page_contrast(self, path):
        status, html = await fetch_page(path)
        assert status == 200, f"Page {path} returned {status}"
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        assert body is not None, f"No body found on {path}"
        bg_match = re.search(r"background(?:-color)?:\s*([#\w]+)", body.get("style", ""))
        bg_color = bg_match.group(1) if bg_match else "#ffffff"
        for tag in soup.find_all(["p", "span", "h1", "h2", "h3", "h4", "h5", "h6", "a", "li", "td", "th", "label"]):
            color_match = re.search(r"color:\s*([#\w]+)", tag.get("style", ""))
            if color_match:
                ratio = contrast_ratio(color_match.group(1), bg_color)
                assert ratio >= 4.5, f"Contrast {ratio:.2f} < 4.5 on {path} for <{tag.name}>"

    @pytest.mark.asyncio
    async def test_css_variables_contrast(self):
        status, html = await fetch_page("/")
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        css_text = " ".join(s.get_text() for s in soup.find_all("style"))
        var_pattern = re.findall(r"--([\w-]+):\s*([#\w]+)", css_text)
        color_vars = {n: v for n, v in var_pattern if "color" in n or "bg" in n or "text" in n}
        assert len(color_vars) >= 2, "Expected at least 2 color CSS variables"
        bg_vars = [v for k, v in color_vars.items() if "bg" in k or "background" in k]
        text_vars = [v for k, v in color_vars.items() if "text" in k or "fg" in k]
        for bg in bg_vars:
            for fg in text_vars:
                assert contrast_ratio(fg, bg) >= 4.5, f"CSS var contrast < 4.5: {fg} on {bg}"

class TestInteractiveAccessibility:
    """Test all interactive elements are accessible."""
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_buttons_have_aria(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for btn in soup.find_all("button"):
            assert (bool(btn.get_text(strip=True)) or btn.get("aria-label") or btn.get("title")), \
                f"Button on {path} missing accessible name: {btn}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_links_have_text(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a"):
            assert (bool(link.get_text(strip=True)) or link.get("aria-label")), \
                f"Link on {path} missing accessible text: {link}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_images_have_alt(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            assert img.get("alt") is not None, f"Image on {path} missing alt: {img}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_inputs_have_labels(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for inp in soup.find_all(["input", "select", "textarea"]):
            if inp.get("type", "text") in ("hidden", "submit", "button"):
                continue
            input_id = inp.get("id")
            has_label = input_id and soup.find("label", attrs={"for": input_id})
            assert (has_label or inp.get("aria-label") or inp.get("placeholder")), \
                f"Input on {path} missing label: {inp}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_focusable_elements_tabindex(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for elem in soup.find_all(["a", "button", "input", "select", "textarea", "tabindex"]):
            tabindex = elem.get("tabindex")
            if tabindex is not None:
                assert tabindex != "-1", f"Element on {path} has tabindex=-1: {elem}"

class TestFormLabels:
    """Test all forms have proper labels."""
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_form_inputs_labeled(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for form in soup.find_all("form"):
            for inp in form.find_all(["input", "select", "textarea"]):
                if inp.get("type", "text") in ("hidden", "submit", "button", "reset"):
                    continue
                input_id = inp.get("id")
                has_label = input_id and soup.find("label", attrs={"for": input_id})
                has_wrapped = inp.find_parent("label") is not None
                assert (has_label or inp.get("aria-label") or has_wrapped), \
                    f"Form input on {path} missing label: {inp}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_required_fields_marked(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for inp in soup.find_all(attrs={"required": True}):
            input_id = inp.get("id")
            has_aria = inp.get("aria-required") == "true"
            has_label = input_id and soup.find("label", attrs={"for": input_id})
            assert (has_aria or (has_label and "*" in has_label.get_text())), \
                f"Required field on {path} not marked: {inp}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_fieldset_for_groups(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        radio_groups = {}
        for radio in soup.find_all("input", attrs={"type": "radio"}):
            name = radio.get("name", "")
            if name:
                radio_groups.setdefault(name, []).append(radio)
        for name, radios in radio_groups.items():
            if len(radios) > 1:
                assert radios[0].find_parent("fieldset") is not None, \
                    f"Radio group '{name}' on {path} not in fieldset"

class TestButtonFocusStates:
    """Test all buttons have proper focus states."""
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_buttons_focusable(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        for btn in soup.find_all("button"):
            assert (btn.get("disabled") is None or btn.get("aria-disabled")), \
                f"Disabled button on {path} missing aria-disabled: {btn}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_focus_styles_defined(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        css_text = " ".join(s.get_text() for s in soup.find_all("style"))
        assert ":focus" in css_text or "focus-visible" in css_text, \
            f"No focus styles defined on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_focus_outline_not_none(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        css_text = " ".join(s.get_text() for s in soup.find_all("style"))
        assert not re.findall(r":focus[^{]*\{[^}]*outline:\s*none", css_text), \
            f"Found :focus with outline:none on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_skip_link_present(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        skip_link = soup.find("a", href="#main-content") or \
            soup.find("a", string=re.compile(r"skip", re.I))
        assert skip_link is not None, f"No skip navigation link on {path}"

class TestLoadingStates:
    """Test all pages have proper loading states."""
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_loading_indicator(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        has_spinner = bool(soup.find(class_=re.compile(r"spinner|loading", re.I)))
        has_skeleton = bool(soup.find(class_=re.compile(r"skeleton|shimmer", re.I)))
        has_aria_busy = bool(soup.find(attrs={"aria-busy": "true"}))
        has_loading_text = bool(soup.find(string=re.compile(r"loading", re.I)))
        assert (has_spinner or has_skeleton or has_aria_busy or has_loading_text), \
            f"No loading indicator on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_async_content_placeholder(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        has_data_loading = bool(soup.find(attrs={"data-loading": True}))
        has_placeholder = bool(soup.find(class_=re.compile(r"placeholder|skeleton", re.I)))
        assert (has_data_loading or has_placeholder), \
            f"No async content placeholder on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_error_state_handling(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        has_error_class = bool(soup.find(class_=re.compile(r"error|alert", re.I)))
        has_role_alert = bool(soup.find(attrs={"role": "alert"}))
        has_error_handler = "onerror" in html or "catch" in html
        assert (has_error_class or has_role_alert or has_error_handler), \
            f"No error state handling on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_empty_state_handling(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        has_empty_class = bool(soup.find(class_=re.compile(r"empty|no-data", re.I)))
        has_empty_text = bool(soup.find(string=re.compile(r"no data|empty|nothing", re.I)))
        assert (has_empty_class or has_empty_text), f"No empty state handling on {path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PAGES)
    async def test_progressive_enhancement(self, path):
        status, html = await fetch_page(path)
        assert status == 200
        soup = BeautifulSoup(html, "html.parser")
        noscript = soup.find("noscript")
        has_fallback = (noscript and bool(noscript.get_text(strip=True))) or \
            bool(soup.find(attrs={"data-fallback": True}))
        assert has_fallback, f"No progressive enhancement fallback on {path}"
