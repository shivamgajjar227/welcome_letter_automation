from pydantic import BaseModel

class PRSiteDataCreate(BaseModel):
    last_name: str
    first_name: str
    gender: str
    city: str
    state: str
    zip_code: str
    status: str
