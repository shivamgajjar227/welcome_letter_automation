from __future__ import annotations

from typing import List

from fastapi import APIRouter

from db.session import SessionLocal
from models.pr_site_data import PRSiteData

router = APIRouter(prefix="/data", tags=["data"])


def _serialize(record: PRSiteData) -> dict:
    return {
        "npi_number": record.npi_number,
        "effective_date": record.effective_date,
        "health_plan": record.health_plan,
        "lines_of_business": record.lines_of_business,
        "last_name": record.last_name,
        "first_name": record.first_name,
        "gender": record.gender,
        "city": record.city,
        "state": record.state,
        "zip_code": record.zip_code,
        "category": record.category,
        "speciality": record.speciality,
        "network": record.network,
        "group_npi": getattr(record, "group_npi", None),
        "status": record.status,
    }


@router.get("/monday-status")
def get_monday_status() -> dict:
    with SessionLocal() as session:
        records: List[PRSiteData] = session.query(PRSiteData).filter(PRSiteData.status == 2).all()
        return {"records": [{"npi_number": r.npi_number} for r in records]}


@router.get("/pr-site")
def get_pr_site_records() -> dict:
    with SessionLocal() as session:
        records: List[PRSiteData] = session.query(PRSiteData).filter(PRSiteData.status == 0).all()
        return {"records": [_serialize(r) for r in records]}


@router.get("/quickcap")
def get_quickcap_records() -> dict:
    with SessionLocal() as session:
        records: List[PRSiteData] = session.query(PRSiteData).filter(PRSiteData.status == 1).all()
        return {"records": [_serialize(r) for r in records]}
