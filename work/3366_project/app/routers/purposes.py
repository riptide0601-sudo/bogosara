from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.purpose import Purpose
from app.schemas.purpose import PurposeCreate, PurposeRead

router = APIRouter(prefix="/purposes", tags=["purposes"])


@router.get("", response_model=list[PurposeRead])
def list_purposes(db: Session = Depends(get_db)):
    return db.scalars(select(Purpose).order_by(Purpose.purpose_name)).all()


@router.post("", response_model=PurposeRead, status_code=201)
def create_purpose(payload: PurposeCreate, db: Session = Depends(get_db)):
    purpose = Purpose(**payload.model_dump())
    db.add(purpose)
    db.commit()
    db.refresh(purpose)
    return purpose


@router.get("/{purpose_id}", response_model=PurposeRead)
def get_purpose(purpose_id: int, db: Session = Depends(get_db)):
    purpose = db.get(Purpose, purpose_id)
    if purpose is None:
        raise HTTPException(status_code=404, detail="Purpose not found")
    return purpose
