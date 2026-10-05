import pytest
from pydantic import ValidationError
from app.config import Settings
from app.schemas import Registration


def test_production_requires_secure_cookie_and_https_origins():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", cors_origins=["https://policy.example"], cookie_secure=False)
    settings = Settings(_env_file=None, environment="production", cors_origins=["https://policy.example"], cookie_secure=True)
    assert settings.cookie_secure
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["http://localhost:5173"])


def test_config_error_does_not_expose_secret_and_db_test_isolation():
    with pytest.raises(ValidationError) as failure:
        Settings(_env_file=None, jwt_secret="private-short-secret")
    assert "private-short-secret" not in str(failure.value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, test_db_name="gov_policy")


def test_password_limits_do_not_truncate():
    value = Registration(email="test@example.com", username="test_user", password="x" * 128)
    assert len(value.password.get_secret_value()) == 128
    for count in [0, 11, 129]:
        with pytest.raises(ValidationError):
            Registration(email="test@example.com", username="test_user", password="x" * count)
