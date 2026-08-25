from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.saved_result import SavedResult
from app.models.user import User
from app.schemas.user import (
    SavedResultCreate,
    SavedResultRead,
    SkinProfileRead,
    SkinProfileUpdate,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


def _to_saved_result_read(saved: SavedResult, product: Product) -> SavedResultRead:
    return SavedResultRead(
        product_id=product.product_id,
        product_name=product.product_name,
        brand=product.brand,
        category=product.category,
        saved_at=saved.saved_at,
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/skin-profile", response_model=SkinProfileRead)
def get_skin_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/skin-profile", response_model=SkinProfileRead)
def update_skin_profile(
    payload: SkinProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/saved-results", response_model=list[SavedResultRead])
def list_saved_results(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(SavedResult, Product)
        .join(Product, Product.product_id == SavedResult.product_id)
        .where(SavedResult.user_id == current_user.user_id)
        .order_by(SavedResult.saved_at.desc())
    )
    return [_to_saved_result_read(saved, product) for saved, product in db.execute(stmt).all()]


@router.post("/me/saved-results", response_model=SavedResultRead, status_code=201)
def save_result(
    payload: SavedResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    saved = db.get(SavedResult, {"user_id": current_user.user_id, "product_id": payload.product_id})
    if saved is None:
        saved = SavedResult(user_id=current_user.user_id, product_id=payload.product_id)
        db.add(saved)
        db.commit()
        db.refresh(saved)

    return _to_saved_result_read(saved, product)


@router.delete("/me/saved-results/{product_id}", status_code=204)
def unsave_result(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = db.get(SavedResult, {"user_id": current_user.user_id, "product_id": product_id})
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved result not found")
    db.delete(saved)
    db.commit()
