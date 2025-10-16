from email.policy import default
import allure
import pytest
from drivers.webdriver_manager import get_driver
from pages.login_page import LoginPage
from pages.monday_page import MondayPage
from pages.pr_site_page import PRSitePage
from pages.quickcap_page import QuickcapPage, logger
from pages.sql_server_page import SqlServerPage
from pages.quickcap_case_page import QuickcapCasePage
from pages.monday_status_page import MondayStatusPage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FirefoxOptions


def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="chrome")
    parser.addoption("--base-url", action="store", default="https://pnstest.quickcap.net")
    parser.addoption("--base-url1", action="store", default="https://pns-mgmt.monday.com/")
    parser.addoption("--base-url2", action="store", default="https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1")
    parser.addoption("--base-url3", action="store", default="https://larch.ad.pns-mgmt.com/Reports_PROD/browse")
    parser.addoption("--base-url4", action="store", default="https://pns-mgmt.monday.com/")
    """Add custom command line options"""
    try:
        parser.addoption("--base-url", action="store", default="", help="Base URL for tests")
        parser.addoption("--browser", action="store", default="chrome", help="Browser to use")
        parser.addoption("--headless", action="store_true", help="Run in headless mode")
    except ValueError as e:
        # Options already exist, ignore the error
        if "already added" in str(e):
            pass
        else:
            raise



@pytest.fixture(scope="function")
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

@pytest.fixture(scope="function")
def sql_server_test(driver, request):
    username = "autoprocess@ad.pns-mgmt.com"
    password = "P%23194714496192ab"
    url_with_auth = f"https://{username}:{password}@larch.ad.pns-mgmt.com/Reports_PROD/browse"
    driver.get(url_with_auth)
    return SqlServerPage(driver)

@pytest.fixture(scope="function")
def quickcap_test_case(driver, request):
    base_url = request.config.getoption("--base-url")
    driver.get(base_url)
    return QuickcapCasePage(driver)

@pytest.fixture(scope="function")
def monday_status_test(driver, request):
    base_url = request.config.getoption("--base-url4")
    driver.get(base_url)
    return MondayStatusPage(driver)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("monday_test", None) \
                 or item.funcargs.get("pr_sites_test", None) \
                 or item.funcargs.get("quickcap_test", None) \
                 or item.funcargs.get("monday_status_test", None)
        if driver:
            try:
                screenshot = driver.driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name=f"screenshot_{item.name}",
                    attachment_type=allure.attachment_type.PNG
                )
            except Exception as e:
                print("Could not attach screenshot:", e)

@pytest.fixture(scope="function")
def open_two_windows(driver):
    driver.get("https://monday-site.com")
    monday_page = MondayPage(driver)
    monday_handle = driver.current_window_handle

    if monday_page.is_login_page():
        monday_page.login("autoprocess@pns-mgmt.com", "@VEnger200@@@@")


@pytest.fixture
def browser(request):
    browser_name = request.config.getoption("--browser")
    headless = request.config.getoption("--headless")

    if browser_name == "chrome":
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            options=chrome_options
        )

    elif browser_name == "firefox":
        firefox_options = FirefoxOptions()
        if headless:
            firefox_options.add_argument("--headless")

        driver = webdriver.Remote(
            command_executor='http://selenium-chrome:4444/wd/hub',  # or selenium-firefox container name
            options=firefox_options
        )

    else:
        raise ValueError(f"Unsupported browser: {browser_name}")

    driver.implicitly_wait(10)
    yield driver
    driver.quit()

