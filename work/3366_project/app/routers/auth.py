from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenRead, UserLogin, UserRead, UserSignup

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenRead, status_code=201)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    existing = db.scalars(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenRead(access_token=create_access_token(user.user_id), user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenRead)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        # 이메일이 없는 경우와 비밀번호가 틀린 경우를 같은 메시지로 묶어, 어느 이메일이
        # 가입돼 있는지 외부에서 유추할 수 없게 한다.
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않아요")
    return TokenRead(access_token=create_access_token(user.user_id), user=UserRead.model_validate(user))
