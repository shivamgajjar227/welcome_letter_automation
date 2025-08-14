import time

from selenium.common import TimeoutException, StaleElementReferenceException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage

class PRPage(BasePage):

    practice_menu = (By)