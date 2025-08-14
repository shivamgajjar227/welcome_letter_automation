from db.session import SessionLocal
from models.pr_site_data import PRSiteData
import time

def test_sql(sql_server_test):
    db = SessionLocal()

    try:
        npis = db.query(PRSiteData.npi_number).filter(PRSiteData.status == 1).all()

        time.sleep(3)
        sql_server_test.click_credential()
        time.sleep(3)
        sql_server_test.click_provider_report()
        time.sleep(3)
        sql_server_test.click_pml_report()
        time.sleep(3)
        sql_server_test.switch_to_report_iframe()
        for (npi,) in npis:
            print(f"Searching report for NPI: {npi}")
            sql_server_test.enter_npi_search(str(npi))
            sql_server_test.click_report_view()
            time.sleep(3)
            address = sql_server_test.get_address()
            record = db.query(PRSiteData).filter(PRSiteData.npi_number == npi,PRSiteData.status == 1).first()
            if record:
                record.address = address
                db.commit()
                print(f" Address saved for NPI {npi}")
            else:
                print(f" NPI {npi} not found in DB.")


    finally:
        db.close()
