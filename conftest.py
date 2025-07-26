from email.policy import default

import pytest
from drivers.webdriver_manager import get_driver
from pages.login_page import LoginPage
from pages.monday_page import MondayPage
from pages.pr_site_page import PRSitePage
from pages.quickcap_page import QuickcapPage


def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chrome")
    parser.addoption("--base-url", action="store", default="https://pnstest.quickcap.net")
    parser.addoption("--base-url1", action="store", default="https://pns-mgmt.monday.com/")
    parser.addoption("--base-url2", action="store", default="https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1")


@pytest.fixture(scope="session")
def driver(request):
    browser = request.config.getoption("--browser")
    driver = get_driver(browser)
    yield driver
    driver.quit()

@pytest.fixture(scope="function")
def quickcap_test(driver, request):
    base_url = request.config.getoption("--base-url")
    driver.get(base_url)
    return QuickcapPage(driver)

@pytest.fixture(scope="function")
def monday_test(driver, request):
    base_url = request.config.getoption("--base-url1")
    driver.get(base_url)
    return MondayPage(driver)

@pytest.fixture(scope="function")
def pr_sites_test(driver, request):
    username = "autoprocess@ad.pns-mgmt.com"
    password = "P%23194714496192ab"
    url_with_auth = f"https://{username}:{password}@pss.ad.pns-mgmt.com"
    driver.get(url_with_auth)
    return PRSitePage(driver)
