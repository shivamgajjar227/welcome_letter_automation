from time import sleep

import pytest
import pages

def test_qc(quickcap_test):
    quickcap_test.choose_company()
    quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")

def test_monday(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
