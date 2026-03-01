from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import CarMileage
from app.schemas.car_mileage import CarMileageCreate, CarMileageOut

router = APIRouter(prefix="/carMileage", tags=["CarMileage"])

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[CarMileageOut])
def read_car_mileage(db: Session = Depends(get_db)):
    return db.query(CarMileage).all()

@router.post("/", response_model=CarMileageOut)
def create_car_mileage(car_mileage: CarMileageCreate, db: Session = Depends(get_db)):
    db_car_mileage = CarMileage(**car_mileage.dict())
    db.add(db_car_mileage)
    db.commit()
    db.refresh(db_car_mileage)
    return db_car_mileage