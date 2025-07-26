from sqlalchemy.orm import Session
from models import PRSiteData
from db.session import SessionLocal  # or wherever you create your Session

def save_scraped_pr_site_data(scraped_data: dict):
    """
    Save a single PR site scraped record to the database.
    """
    db: Session = SessionLocal()
    try:
        record = PRSiteData(
            last_name=scraped_data.get("last_name"),
            first_name=scraped_data.get("first_name"),
            gender=scraped_data.get("gender"),
            npi_number=scraped_data.get("npi_number"),
            city=scraped_data.get("city"),
            state=scraped_data.get("state"),
            zip_code=scraped_data.get("zip_code"),
            status=scraped_data.get("status", False)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as e:
        db.rollback()
        print("Error saving scraped PR site data:", e)
        raise
    finally:
        db.close()
