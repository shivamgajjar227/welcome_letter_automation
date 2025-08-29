from sqlalchemy.orm import Session
import re
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


def split_address(raw_address: str):
    parts = raw_address.split(",")

    # First part may contain Suite
    address_line1, address_line2 = None, None
    suite_pattern = re.compile(r"(.*?)(Suite\s*\d+.*)", re.IGNORECASE)
    match = suite_pattern.match(parts[0].strip())

    if match:
        address_line1 = match.group(1).strip()
        address_line2 = match.group(2).strip()
    else:
        address_line1 = parts[0].strip()

    city = parts[1].strip() if len(parts) > 1 else None
    state_zip = parts[2].strip().split(" ") if len(parts) > 2 else []

    state = state_zip[0] if len(state_zip) > 0 else None
    zip_code = state_zip[1] if len(state_zip) > 1 else None

    return {
        "address_line1": address_line1,
        "address_line2": address_line2,
        "city": city,
        "state": state,
        "zip_code": zip_code
    }
