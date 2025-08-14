from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from sqlalchemy.orm import Session
import time


def test_monday_status(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
    monday_test.click_welcome_letter_qc()

    db: Session = SessionLocal()
    try:
        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 2).all()

        if not npi_records:
            print("No NPI records with status = 2.")
            return

        first_iteration = True  # Flag to track first iteration

        for record in npi_records:
            try:
                if first_iteration:
                    monday_test.click_search_button()
                    first_iteration = False

                monday_test.enter_npi_button(record.npi_number)
                time.sleep(2)
                monday_test.click_not_started()
                monday_test.click_done_button()
                time.sleep(2)
                monday_test.click_cross_button()
                time.sleep(2)
                record.status = 3
                db.commit()
                print(f" NPI {record.npi_number} processed successfully.\n")

            except Exception as e:
                print(f"Error processing NPI {record.npi_number}: {str(e)}")
                continue

        monday_test.driver.close()

    finally:
        db.close()