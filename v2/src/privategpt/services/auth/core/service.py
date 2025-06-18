from __future__ import annotations

from sqlalchemy.orm import Session

from privategpt.shared.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from privategpt.shared.logging import get_logger
from privategpt.infra.database.models import User
from privategpt.services.auth.schemas import (
    UserCreate,
    UserLogin,
    Token,
    UserOut,
)

logger = get_logger("auth-v2")


class AuthService:
    """Business logic for registration & login."""

    def __init__(self, db: Session):
        self.db = db

    def register(self, data: UserCreate) -> UserOut:
        if self.db.query(User).filter(User.email == data.email).first():
            raise ValueError("Email already registered")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info("new_user", email=user.email)
        return UserOut.model_validate(user)  # type: ignore[arg-type]

    def login(self, data: UserLogin) -> Token:
        user: User | None = (
            self.db.query(User).filter(User.email == data.email).first()
        )
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Invalid credentials")
        access = create_access_token(
            {"sub": user.email, "role": user.role, "id": user.id}
        )
        return Token(access_token=access, expires_in=86400) 