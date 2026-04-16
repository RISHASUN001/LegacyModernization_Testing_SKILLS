from playwright.sync_api import Page

def test_successful_login(page: Page) -> None:
    """Test Successful Login workflow."""
    page.goto('http://localhost:5001')
    page.wait_for_load_state('networkidle')
    assert page.url
