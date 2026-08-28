from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.routine_history import RoutineHistory
from app.models.routine_item import RoutineItem
from app.models.saved_result import SavedResult
from app.models.user import User
from app.routine_analysis import analyze_routine, build_item_description, parse_json_list
from app.schemas.routine import (
    RoutineAnalysisRead,
    RoutineHistoryProductRead,
    RoutineHistoryRead,
    RoutineItemCreate,
    RoutineItemRead,
)
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


def _to_analysis_read(result) -> RoutineAnalysisRead:
    return RoutineAnalysisRead(
        product_count=result.product_count,
        ingredient_count=result.ingredient_count,
        headline=result.headline,
        overall_description=result.overall_description,
        hydration_note=result.hydration_note,
        hydration_count=result.hydration_count,
        occlusion_count=result.occlusion_count,
        hydration_ingredients=result.hydration_ingredients,
        occlusion_ingredients=result.occlusion_ingredients,
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


@router.get("/me/routine/analysis", response_model=RoutineAnalysisRead)
def get_routine_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product_ids = list(
        db.scalars(
            select(RoutineItem.product_id).where(RoutineItem.user_id == current_user.user_id)
        )
    )
    result = analyze_routine(product_ids, current_user.skin_types, db)
    return _to_analysis_read(result)


def _to_routine_history_read(history: RoutineHistory, products_by_id: dict[str, Product]) -> RoutineHistoryRead:
    products = [
        RoutineHistoryProductRead(product_id=pid, product_name=p.product_name, brand=p.brand)
        for pid in history.product_ids
        if (p := products_by_id.get(pid)) is not None
    ]
    return RoutineHistoryRead(
        history_id=history.history_id,
        headline=history.headline,
        product_count=len(history.product_ids),
        products=products,
        saved_at=history.saved_at,
    )


@router.get("/me/routine/history", response_model=list[RoutineHistoryRead])
def list_routine_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entries = list(
        db.scalars(
            select(RoutineHistory)
            .where(RoutineHistory.user_id == current_user.user_id)
            .order_by(RoutineHistory.saved_at.desc())
        )
    )
    all_product_ids = {pid for entry in entries for pid in entry.product_ids}
    products_by_id = {
        p.product_id: p
        for p in db.scalars(select(Product).where(Product.product_id.in_(all_product_ids)))
    }
    return [_to_routine_history_read(entry, products_by_id) for entry in entries]


@router.get("/me/routine/history/{history_id}/analysis", response_model=RoutineAnalysisRead)
def get_routine_history_analysis(
    history_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """저장된 조합 기록 하나를 그때 제품 구성(product_ids) 그대로 다시 분석해서 보여준다 —
    "조합 기록" 카드를 눌렀을 때 그 시점 조합의 분석표를 보는 용도. 지금 등록된 조합
    (RoutineItem)과는 무관하게, 이 기록의 product_ids만 갖고 계산한다."""
    entry = db.get(RoutineHistory, history_id)
    if entry is None or entry.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Routine history entry not found")

    result = analyze_routine(entry.product_ids, current_user.skin_types, db)
    return _to_analysis_read(result)


@router.post("/me/routine/history", response_model=RoutineHistoryRead, status_code=201)
def save_routine_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """지금 등록된 조합(RoutineItem 전체)을 그대로 스냅샷으로 저장한다 — "이 조합
    저장하기" 버튼 전용. 조합이 비어 있으면 저장할 게 없으므로 막는다."""
    product_ids = list(
        db.scalars(
            select(RoutineItem.product_id)
            .where(RoutineItem.user_id == current_user.user_id)
            .order_by(RoutineItem.added_at.asc())
        )
    )
    if not product_ids:
        raise HTTPException(status_code=400, detail="등록된 화장품이 없어서 저장할 조합이 없어요.")

    result = analyze_routine(product_ids, current_user.skin_types, db)
    entry = RoutineHistory(user_id=current_user.user_id, product_ids=product_ids, headline=result.headline)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    products_by_id = {p.product_id: p for p in db.scalars(select(Product).where(Product.product_id.in_(product_ids)))}
    return _to_routine_history_read(entry, products_by_id)


@router.delete("/me/routine/history/{history_id}", status_code=204)
def delete_routine_history(
    history_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.get(RoutineHistory, history_id)
    if entry is None or entry.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Routine history entry not found")
    db.delete(entry)
    db.commit()
