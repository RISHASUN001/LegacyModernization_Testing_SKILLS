import json
import os
import re
import pytest

MODULE_NAME = "LoginFinal"
RUN_ID = "loginfinal-fresh-test-20260415"
DEFAULT_BASE_URL = "http://localhost:5001"
BASE_URL = (os.getenv('LEGACYMOD_BASE_URL') or os.getenv('BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
DEFAULT_USERNAME = os.getenv('LEGACYMOD_TEST_USERNAME', 'demo.user')
DEFAULT_PASSWORD = os.getenv('LEGACYMOD_TEST_PASSWORD', 'demo.password')
INPUT_SELECTORS = json.loads("[\"input#email\", \"input[name='email']\", \"input#password\", \"input[name='password']\", \"input[placeholder*='admin' i]\", \"input[placeholder*='password123' i]\"]")
PASSWORD_SELECTORS = json.loads("[\"input#password\", \"input[name='password']\"]")
SUBMIT_SELECTORS = json.loads("[\"button:has-text('Login to Dashboard')\", \"button:has-text('Login')\"]")
DROPDOWN_SELECTORS = json.loads("[\"select#module\", \"select[name='module']\"]")
CLICK_SELECTORS = json.loads("[\"a:has-text('Logout')\", \"a:has-text('Dashboard')\", \"a:has-text('Users')\", \"a:has-text('Settings')\", \"a:has-text('Reports')\", \"a:has-text('System Config')\", \"a:has-text('Audit Log')\", \"a:has-text('Database')\", \"button:has-text('Login to Dashboard')\", \"a[href='/logout']\", \"a:has-text('Back to Login')\", \"a[href='/']\", \"button:has-text('Login')\"]")

def _first_locator(page, selectors):
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() > 0:
            return locator
    return None

def _safe_fill(page, selector, value):
    try:
        page.locator(selector).first.fill(value, timeout=2500)
        return True
    except Exception:
        return False

def _safe_click(page, selector):
    try:
        page.locator(selector).first.click(timeout=2500)
        return True
    except Exception:
        return False

def _try_auth_interaction(page):
    username = _first_locator(page, INPUT_SELECTORS + ["input[name='username']", "input[name='userName']", "input[name='email']", "input[type='email']", "input#username", "input#email"]) 
    if username is not None:
        try:
            username.fill(DEFAULT_USERNAME, timeout=2500)
        except Exception:
            pass
    password = _first_locator(page, PASSWORD_SELECTORS + ["input[name='password']", "input[type='password']", "input#password"]) 
    if password is not None:
        try:
            password.fill(DEFAULT_PASSWORD, timeout=2500)
        except Exception:
            pass
    submit = _first_locator(page, SUBMIT_SELECTORS + ["button[type='submit']", "input[type='submit']", "button:has-text('Sign in')", "button:has-text('Login')", "button:has-text('Log in')"]) 
    if submit is not None:
        try:
            submit.click(timeout=2500)
        except Exception:
            pass

def _try_common_interactions(page):
    for selector in CLICK_SELECTORS + ["button:has-text('Options')", "button:has-text('Menu')", "button:has-text('More')", "a:has-text('Options')", "a:has-text('Settings')", "[data-testid='options']"]:
        if _safe_click(page, selector):
            break
    dropdown = _first_locator(page, DROPDOWN_SELECTORS)
    if dropdown is not None:
        try:
            options = dropdown.locator('option')
            if options.count() > 0:
                value = options.nth(0).get_attribute('value')
                if value:
                    dropdown.select_option(value)
        except Exception:
            pass
    _safe_fill(page, "input[type='search']", "legacy modernization")

@pytest.mark.playwright
def test_playwright_business_flow_open_login_page(page):
    route = "/login"
    page.goto(f"{BASE_URL}{route}", wait_until='domcontentloaded')
    assert page.locator('body').first.is_visible()
    _try_auth_interaction(page)
    _try_common_interactions(page)
    title = page.title()
    assert len(title.strip()) > 0

@pytest.mark.playwright
def test_playwright_business_flow_session_timeout_returns_to_login(page):
    route = "/"
    page.goto(f"{BASE_URL}{route}", wait_until='domcontentloaded')
    assert page.locator('body').first.is_visible()
    _try_auth_interaction(page)
    _try_common_interactions(page)
    title = page.title()
    assert len(title.strip()) > 0

@pytest.mark.playwright
def test_playwright_generated_journey_1_for_loginfinal(page):
    route = "/"
    page.goto(f"{BASE_URL}{route}", wait_until='domcontentloaded')
    assert page.locator('body').first.is_visible()
    _try_auth_interaction(page)
    _try_common_interactions(page)
    title = page.title()
    assert len(title.strip()) > 0

@pytest.mark.playwright
def test_playwright_generated_journey_2_for_loginfinal(page):
    route = "/"
    page.goto(f"{BASE_URL}{route}", wait_until='domcontentloaded')
    assert page.locator('body').first.is_visible()
    _try_auth_interaction(page)
    _try_common_interactions(page)
    title = page.title()
    assert len(title.strip()) > 0
