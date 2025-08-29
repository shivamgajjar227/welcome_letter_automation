import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.base_class import Base

class NPIAddress(Base):
    __tablename__ = "npi_address"

    id = Column(Integer, primary_key=True, index=True)
    npi = Column(Integer, nullable=False)
    address_line1 = Column(String(500), nullable=True)
    address_line2 = Column(String(500), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    remarks = Column(String(500), nullable=True)
    update = Column(Integer, nullable=True)
    group_npi = Column(Integer, nullable=False)
    name = Column(String(500), nullable=True)



    # pr_site = relationship("PRSiteData", back_populates="npi_details")
