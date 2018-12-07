from .pages.login import LoginPage

def check_user_logged_in(driver, user_name):
    button = driver.find_element_by_css_selector('button[data-target=user-menu]')
    assert button.text == user_name

def test_login(driver, base_url):
    """
    TC38 - Sign in with valid username and password
    """
    page = LoginPage(driver, base_url)
    page.username_field().send_keys("admin")
    page.password_field().send_keys("password")
    page.signin_button().click()
    check_user_logged_in(driver, 'admin')
