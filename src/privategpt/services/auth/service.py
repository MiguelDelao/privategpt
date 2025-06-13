from __future__ import annotations

from sqlalchemy.orm import Session

from privategpt.shared.security import create_access_token, hash_password, verify_password
from privategpt.shared.logging import get_logger

from .schemas import Token, UserCreate, UserLogin, UserOut
from ...infra.database.models import User  # relative import from root package

logger = get_logger("auth_service")


class AuthService:
    """Pure application logic – independent from FastAPI."""

    def __init__(self, db: Session):
        self._db = db

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def register(self, data: UserCreate) -> UserOut:
        if self._db.query(User).filter(User.email == data.email).first():
            raise ValueError("Email already registered")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            role="user",
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        logger.info("New user registered", email=data.email)
        return UserOut.from_orm(user)  # type: ignore[arg-type]

    def login(self, data: UserLogin) -> Token:
        user: User | None = self._db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid credentials")
        token = create_access_token({"sub": user.email, "role": user.role, "id": user.id})
        return Token(access_token=token, expires_in=60 * 60 * 24)

    def me(self, user: User) -> UserOut:
        return UserOut.from_orm(user)  # type: ignore[arg-type] 