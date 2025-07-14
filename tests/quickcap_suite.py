import time
from time import sleep

import pytest
import pages

def test_qc(quickcap_test):
    quickcap_test.choose_company()
    quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
    time.sleep(3)
    quickcap_test.choose_credentialing_tab()
    time.sleep(3)
    quickcap_test.choose_practitioner_data()
    time.sleep(3)
    quickcap_test.enter_npi(1841378346)
    quickcap_test.click_quick_add_button()
    quickcap_test.switch_to_new_window()
    quickcap_test.select_category_dropdown("CRNA - CRNA")
    time.sleep(3)
    quickcap_test.click_quick_add_window_npi_button(1841378346)
    time.sleep(3)
    quickcap_test.select_provider_type_dropdown("PHYSICIAN EXTENDER")
    time.sleep(3)
    quickcap_test.enter_provider_id("1234")
    quickcap_test.select_primary_speciality_dropdown("DM - DERMATOLOGY MOHS ONLY")
    quickcap_test.switch_back_to_main()


def test_monday(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")

