from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import SessionLocal
from app.db.models import Weight, BloodPressure, Diet, Workout, SafetyMeetingDaily
from app.schemas.health_day import HealthDayOut, HealthDayUpsert
from app.schemas.health_dashboard import HealthDashboardOut, HealthDaySummary, BloodPressurePoint
from app.schemas.weight import WeightOut
from app.schemas.blood_pressure import BloodPressureOut
from app.schemas.diet import DietOut
from app.schemas.workout import WorkoutOut
from app.schemas.safety_meeting import SafetyMeetingDailyOut, SafetyMeetingDailyUpsert

router = APIRouter(prefix="/health", tags=["Health"])


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def _get_day_snapshot(db: Session, day: date) -> HealthDayOut:
  w = db.query(Weight).filter(Weight.entry_date == day).first()
  bp = db.query(BloodPressure).filter(BloodPressure.entry_date == day).first()
  diet = db.query(Diet).filter(Diet.log_date == day).order_by(Diet.id.asc()).all()
  workouts = db.query(Workout).filter(Workout.workout_date == day).order_by(Workout.id.asc()).all()

  return HealthDayOut(
    weight=WeightOut.model_validate(w) if w else None,
    blood_pressure=BloodPressureOut.model_validate(bp) if bp else None,
    diet=[DietOut.model_validate(x) for x in diet],
    workouts=[WorkoutOut.model_validate(x) for x in workouts],
  )


@router.get("/day", response_model=HealthDayOut)
def read_day(date: date, db: Session = Depends(get_db)):
  return _get_day_snapshot(db, date)


@router.put("/day", response_model=HealthDayOut)
def upsert_day(date: date, payload: HealthDayUpsert, db: Session = Depends(get_db)):
  # --- Weight (one/day) ---
  if payload.weight and payload.weight.weight is not None:
    existing = db.query(Weight).filter(Weight.entry_date == date).first()
    if existing:
      existing.weight = payload.weight.weight
    else:
      db.add(Weight(entry_date=date, weight=payload.weight.weight))

  # --- Blood pressure (one/day) ---
  if payload.blood_pressure and (payload.blood_pressure.systolic is not None or payload.blood_pressure.diastolic is not None):
    existing = db.query(BloodPressure).filter(BloodPressure.entry_date == date).first()
    if existing:
      if payload.blood_pressure.systolic is not None:
        existing.systolic = payload.blood_pressure.systolic
      if payload.blood_pressure.diastolic is not None:
        existing.diastolic = payload.blood_pressure.diastolic
    else:
      db.add(
        BloodPressure(
          entry_date=date,
          systolic=payload.blood_pressure.systolic,
          diastolic=payload.blood_pressure.diastolic,
        )
      )

  # --- Diet (multi/day) ---
  for item in payload.diet or []:
    # if id is provided, update; else create
    if item.id:
      row = db.query(Diet).filter(Diet.id == item.id).first()
      if not row:
        raise HTTPException(status_code=404, detail=f"Diet id {item.id} not found")
      row.log_date = date
      row.meal = item.meal
      row.food = item.food
      row.calories = item.calories
      row.confidence = item.confidence
    else:
      db.add(
        Diet(
          log_date=date,
          meal=item.meal,
          food=item.food,
          calories=item.calories,
          confidence=item.confidence,
        )
      )

  # --- Workouts (multi/day) ---
  for item in payload.workouts or []:
    if item.id:
      row = db.query(Workout).filter(Workout.id == item.id).first()
      if not row:
        raise HTTPException(status_code=404, detail=f"Workout id {item.id} not found")
      row.workout_date = date
      row.workout = item.workout
      row.calories_burnt = item.calories_burnt
    else:
      db.add(
        Workout(
          workout_date=date,
          workout=item.workout,
          calories_burnt=item.calories_burnt,
        )
      )

  db.commit()
  return _get_day_snapshot(db, date)


@router.get("/safety-meeting", response_model=SafetyMeetingDailyOut)
def read_safety_meeting(date: date, db: Session = Depends(get_db)):
  row = db.query(SafetyMeetingDaily).filter(SafetyMeetingDaily.entry_date == date).first()
  return SafetyMeetingDailyOut(entry_date=date, completed=bool(row))


@router.put("/safety-meeting", response_model=SafetyMeetingDailyOut)
def upsert_safety_meeting(date: date, payload: SafetyMeetingDailyUpsert, db: Session = Depends(get_db)):
  row = db.query(SafetyMeetingDaily).filter(SafetyMeetingDaily.entry_date == date).first()

  if payload.completed:
    if not row:
      db.add(SafetyMeetingDaily(entry_date=date))
  elif row:
    db.delete(row)

  db.commit()
  return SafetyMeetingDailyOut(entry_date=date, completed=payload.completed)


@router.delete("/diet/{diet_id}")
def delete_diet(diet_id: int, db: Session = Depends(get_db)):
  row = db.query(Diet).filter(Diet.id == diet_id).first()
  if not row:
    raise HTTPException(status_code=404, detail="Diet entry not found")
  db.delete(row)
  db.commit()
  return {"ok": True}


@router.delete("/workout/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
  row = db.query(Workout).filter(Workout.id == workout_id).first()
  if not row:
    raise HTTPException(status_code=404, detail="Workout entry not found")
  db.delete(row)
  db.commit()
  return {"ok": True}

def _get_dashboard(db: Session, end_date: date, days: int) -> HealthDashboardOut:
  if days < 1:
    days = 1
  if days > 31:
    days = 31

  start_date = end_date - timedelta(days=days - 1)

  # --- Weight: one/day ---
  weights = (
    db.query(Weight.entry_date, Weight.weight)
    .filter(Weight.entry_date >= start_date, Weight.entry_date <= end_date)
    .all()
  )
  weight_map = {d: w for (d, w) in weights}

  # --- BP: one/day ---
  bps = (
    db.query(BloodPressure.entry_date, BloodPressure.systolic, BloodPressure.diastolic)
    .filter(BloodPressure.entry_date >= start_date, BloodPressure.entry_date <= end_date)
    .all()
  )
  bp_map = {d: (s, dia) for (d, s, dia) in bps}

  # --- Diet calories: many/day -> sum/day ---
  diet_sums = (
    db.query(Diet.log_date, func.coalesce(func.sum(Diet.calories), 0))
    .filter(Diet.log_date >= start_date, Diet.log_date <= end_date)
    .group_by(Diet.log_date)
    .all()
  )
  diet_map = {d: int(total or 0) for (d, total) in diet_sums}

  # --- Workout calories: many/day -> sum/day ---
  workout_sums = (
    db.query(Workout.workout_date, func.coalesce(func.sum(Workout.calories_burnt), 0))
    .filter(Workout.workout_date >= start_date, Workout.workout_date <= end_date)
    .group_by(Workout.workout_date)
    .all()
  )
  workout_map = {d: int(total or 0) for (d, total) in workout_sums}

  series = []
  for i in range(days):
    day = start_date + timedelta(days=i)
    calories_in = diet_map.get(day, 0)
    calories_out = workout_map.get(day, 0)
    net = calories_in - calories_out

    w = weight_map.get(day, None)
    bp = bp_map.get(day, None)

    series.append(
      HealthDaySummary(
        date=day,
        weight=w,
        systolic=bp[0] if bp else None,
        diastolic=bp[1] if bp else None,
        calories_in=calories_in,
        calories_out=calories_out,
        calories_net=net,
      )
    )

  # last 7 BP entries (most recent first, within range)
  bp_last = (
    db.query(BloodPressure.entry_date, BloodPressure.systolic, BloodPressure.diastolic)
    .filter(BloodPressure.entry_date <= end_date)
    .order_by(BloodPressure.entry_date.desc())
    .limit(7)
    .all()
  )

  bp_last_7 = [
    BloodPressurePoint(date=d, systolic=s, diastolic=dia)
    for (d, s, dia) in bp_last
    if s is not None and dia is not None
  ]

  return HealthDashboardOut(end_date=end_date, days=days, series=series, bp_last_7=bp_last_7)


@router.get("/dashboard", response_model=HealthDashboardOut)
def get_dashboard(end_date: date, days: int = 7, db: Session = Depends(get_db)):
  return _get_dashboard(db, end_date=end_date, days=days)
