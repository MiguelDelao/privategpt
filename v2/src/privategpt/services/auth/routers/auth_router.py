from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from privategpt.infra.database.session import get_db
from privategpt.shared.security import decode_token

from privategpt.services.auth.schemas import UserCreate, UserLogin, Token, UserOut
from privategpt.services.auth.service import AuthService
from privategpt.infra.database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _svc(db: Session = Depends(get_db)) -> AuthService:  # noqa
    return AuthService(db)


async def _current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, svc: AuthService = Depends(_svc)):
    try:
        return svc.register(data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/login", response_model=Token)
def login(data: UserLogin, svc: AuthService = Depends(_svc)):
    try:
        return svc.login(data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(_current_user)):
    return UserOut.from_orm(user)  # type: ignore[arg-type] 