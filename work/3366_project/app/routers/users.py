from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.routine_item import RoutineItem
from app.models.saved_result import SavedResult
from app.models.user import User
from app.routine_analysis import analyze_routine, build_item_description, parse_json_list
from app.schemas.routine import RoutineAnalysisRead, RoutineItemCreate, RoutineItemRead
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


def _to_routine_item_read(item: RoutineItem, product: Product) -> RoutineItemRead:
    return RoutineItemRead(
        product_id=product.product_id,
        product_name=product.product_name,
        brand=product.brand,
        category=product.category,
        added_at=item.added_at,
        description=build_item_description(product),
        key_ingredients=parse_json_list(product.key_ingredients),
        key_purposes=parse_json_list(product.key_purposes),
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


@router.get("/me/routine", response_model=list[RoutineItemRead])
def list_routine(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(RoutineItem, Product)
        .join(Product, Product.product_id == RoutineItem.product_id)
        .where(RoutineItem.user_id == current_user.user_id)
        .order_by(RoutineItem.added_at.asc())
    )
    return [_to_routine_item_read(item, product) for item, product in db.execute(stmt).all()]


@router.post("/me/routine", response_model=RoutineItemRead, status_code=201)
def add_to_routine(
    payload: RoutineItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    item = db.get(RoutineItem, {"user_id": current_user.user_id, "product_id": payload.product_id})
    if item is None:
        item = RoutineItem(user_id=current_user.user_id, product_id=payload.product_id)
        db.add(item)
        db.commit()
        db.refresh(item)

    return _to_routine_item_read(item, product)


@router.delete("/me/routine/{product_id}", status_code=204)
def remove_from_routine(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(RoutineItem, {"user_id": current_user.user_id, "product_id": product_id})
    if item is None:
        raise HTTPException(status_code=404, detail="Routine item not found")
    db.delete(item)
    db.commit()


@router.get("/me/routine/analysis", response_model=RoutineAnalysisRead)
def get_routine_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product_ids = list(
        db.scalars(
            select(RoutineItem.product_id).where(RoutineItem.user_id == current_user.user_id)
        )
    )
    result = analyze_routine(product_ids, current_user.skin_types, db)
    return RoutineAnalysisRead(
        product_count=result.product_count,
        ingredient_count=result.ingredient_count,
        headline=result.headline,
        overall_description=result.overall_description,
        hydration_note=result.hydration_note,
        skin_type_notes=[
            {
                "skin_type": note.skin_type,
                "risk_ingredients": [vars(i) for i in note.risk_ingredients],
                "good_ingredients": [vars(i) for i in note.good_ingredients],
            }
            for note in result.skin_type_notes
        ],
        relations=[vars(r) for r in result.relations],
    )
