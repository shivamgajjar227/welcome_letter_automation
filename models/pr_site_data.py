from xmlrpc.client import Boolean

from sqlalchemy import Column, Integer, String , Boolean
from db.base_class import Base  # Assuming you already have Base from database setup

class PRSiteData(Base):
    __tablename__ = "pr_site_data"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    gender = Column(String(100), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    status = Column(Integer, nullable=True)
    npi_number = Column(Integer, nullable=False)
    effective_date = Column(String(500), nullable=True)
    health_plan = Column(String(500), nullable=True)
    lines_of_business = Column(String(500), nullable=True)
    category = Column(String(500), nullable=True)

