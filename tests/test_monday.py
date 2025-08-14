from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from sqlalchemy.orm import Session


def test_monday(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
    monday_test.click_welcome_letter_qc()
    npis = monday_test.get_pr_site_npis()
    print(npis)

    db: Session = SessionLocal()

    try:
        for entry in npis:
            new_row = PRSiteData(
                npi_number=entry.get("npi_number"),
                effective_date=entry.get("effective_date"),
                health_plan=entry.get("health_plan"),
                lines_of_business=entry.get("lines_of_business"),
                status=0
            )
            db.add(new_row)
            print(f"Inserted row: {entry}")

        db.commit()
        print("All NPIs inserted into pr_site_data table.")
    except Exception as e:
        db.rollback()
        print(" Error inserting data:", e)
    finally:
        db.close()
