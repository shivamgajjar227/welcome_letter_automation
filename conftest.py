from email.policy import default

import pytest
from drivers.webdriver_manager import get_driver
from pages.login_page import LoginPage

def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chrome")
    parser.addoption("--base-url", action="store", default="https://example.com")
    parser.addoption("--base-url1", action="store", default="https://example.com")

@pytest.fixture(scope="session")
def driver(request):
    browser = request.config.getoption("--browser")
    driver = get_driver(browser)
    yield driver
    driver.quit()

# @pytest.fixture(scope="function")
# def login_page(driver, request):
#     base_url = request.config.getoption("--base-url")
#     driver.get(base_url)
#     return LoginPage(driver)

@pytest.fixture(scope="function")
def url_1(driver, request):
    base_url = request.config.getoption("--base-url1")
    driver.get(base_url)
    return LoginPage(driver)

