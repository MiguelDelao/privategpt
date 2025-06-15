from privategpt.services.auth.service import AuthService
from privategpt.services.auth.schemas import UserCreate, UserLogin
from privategpt.infra.database.models import Base, User


def test_register_success(db_session):
    svc = AuthService(db_session)
    data = UserCreate(email="alice@example.com", password="secretpass")
    user = svc.register(data)
    assert user.email == "alice@example.com"
    assert db_session.query(User).count() == 1


def test_register_duplicate(db_session):
    svc = AuthService(db_session)
    data = UserCreate(email="dup@example.com", password="secretpass")
    svc.register(data)
    try:
        svc.register(data)
    except ValueError as e:
        assert "already" in str(e)
    else:
        assert False, "expected ValueError"


def test_login_success(db_session):
    svc = AuthService(db_session)
    svc.register(UserCreate(email="bob@example.com", password="secretpass"))
    token = svc.login(UserLogin(email="bob@example.com", password="secretpass"))
    assert token.access_token
    assert token.expires_in > 0


def test_login_wrong_password(db_session):
    svc = AuthService(db_session)
    svc.register(UserCreate(email="bob2@example.com", password="secretpass"))
    try:
        svc.login(UserLogin(email="bob2@example.com", password="wrong"))
    except ValueError as e:
        assert "Invalid" in str(e)
    else:
        assert False, "expected ValueError" 