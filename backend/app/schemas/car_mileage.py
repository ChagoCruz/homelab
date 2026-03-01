from pydantic import BaseModel
from datetime import date

class CarMileageCreate(BaseModel):
    log_date: date
    odometer: int
    
class CarMileageOut(CarMileageCreate):
    id: int
    class Config:
        orm_mode = True