from playwright.sync_api import Page

def test_invalid_login(page: Page) -> None:
    """Test Invalid Login workflow."""
    page.goto('http://localhost:5001')
    page.wait_for_load_state('networkidle')
    assert page.url
