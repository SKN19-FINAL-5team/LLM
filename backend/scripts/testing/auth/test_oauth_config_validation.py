"""
Unit tests for OAuth config validation

작성일: 2026-02-06
설명: OAuth 크리덴셜 미설정 시 방어 코드 검증 (Unit - 모킹 사용)
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.auth.oauth import GoogleOAuth, OAuthConfigError
from app.common.config import AuthConfig


def _make_auth_config(**overrides) -> AuthConfig:
    """테스트용 AuthConfig를 생성합니다."""
    defaults = {
        "JWT_SECRET_KEY": "test_secret",
        "BACKEND_URL": "http://localhost:8000",
        "FRONTEND_URL": "http://localhost:5173",
    }
    defaults.update(overrides)
    return AuthConfig(**defaults)


# ============================================================
# AuthConfig 프로퍼티 테스트
# ============================================================


@pytest.mark.unit
def test_google_oauth_configured_true():
    """Google client_id, secret 모두 있을 때 True"""
    config = _make_auth_config(
        GOOGLE_CLIENT_ID="test-id",
        GOOGLE_CLIENT_SECRET="test-secret",
    )
    assert config.is_google_oauth_configured is True


@pytest.mark.unit
def test_google_oauth_configured_false_missing_id():
    """Google client_id None → False"""
    config = _make_auth_config(
        GOOGLE_CLIENT_SECRET="test-secret",
    )
    assert config.is_google_oauth_configured is False


@pytest.mark.unit
def test_google_oauth_configured_false_empty_string():
    """Google client_id 빈 문자열 → False"""
    config = _make_auth_config(
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="test-secret",
    )
    assert config.is_google_oauth_configured is False


@pytest.mark.unit
def test_google_oauth_configured_false_missing_secret():
    """Google secret만 None → False"""
    config = _make_auth_config(
        GOOGLE_CLIENT_ID="test-id",
    )
    assert config.is_google_oauth_configured is False


@pytest.mark.unit
def test_naver_oauth_configured():
    """Naver 크리덴셜 검증 - 모두 있으면 True, 없으면 False"""
    config_with = _make_auth_config(
        NAVER_CLIENT_ID="test-id",
        NAVER_CLIENT_SECRET="test-secret",
    )
    assert config_with.is_naver_oauth_configured is True

    config_without = _make_auth_config()
    assert config_without.is_naver_oauth_configured is False


# ============================================================
# OAuthConfigError 테스트
# ============================================================


@pytest.mark.unit
def test_get_authorization_url_raises_config_error():
    """Google client_id None → OAuthConfigError 발생"""
    config = _make_auth_config()  # 크리덴셜 없음
    google = GoogleOAuth(config)

    with pytest.raises(OAuthConfigError, match="Google OAuth"):
        google.get_authorization_url()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exchange_code_raises_config_error():
    """토큰 교환 시 크리덴셜 없으면 OAuthConfigError"""
    config = _make_auth_config()
    google = GoogleOAuth(config)

    with pytest.raises(OAuthConfigError, match="Google OAuth"):
        await google.exchange_code_for_token("fake_code")


@pytest.mark.unit
def test_get_authorization_url_works_with_credentials():
    """정상 크리덴셜 → URL 생성 성공"""
    config = _make_auth_config(
        GOOGLE_CLIENT_ID="test-id",
        GOOGLE_CLIENT_SECRET="test-secret",
    )
    google = GoogleOAuth(config)

    url, state = google.get_authorization_url()
    assert "accounts.google.com" in url
    assert "test-id" in url
    assert len(state) > 0


# ============================================================
# 라우트 에러 리다이렉트 테스트
# ============================================================


@pytest.mark.unit
def test_auth_route_redirects_on_config_error():
    """라우트에서 OAuthConfigError → oauth_not_configured 리다이렉트"""
    from fastapi.testclient import TestClient

    from app.api.auth import router

    app = __import__("fastapi", fromlist=["FastAPI"]).FastAPI()
    app.include_router(router)

    with (
        patch("app.api.auth.AuthService") as mock_service_cls,
        patch("app.api.auth.limiter") as mock_limiter,
    ):
        # limiter를 무력화
        mock_limiter.limit.return_value = lambda f: f
        mock_service = mock_service_cls.return_value
        mock_service.get_google_auth_url.side_effect = OAuthConfigError("test")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/auth/google", follow_redirects=False)

        assert response.status_code == 307
        assert "oauth_not_configured" in response.headers.get("location", "")


@pytest.mark.unit
def test_callback_route_config_error_vs_general_error():
    """콜백에서 OAuthConfigError와 일반 Exception 구분"""
    from fastapi.testclient import TestClient

    from app.api.auth import router

    app = __import__("fastapi", fromlist=["FastAPI"]).FastAPI()
    app.include_router(router)

    # OAuthConfigError → oauth_not_configured
    with (
        patch("app.api.auth.AuthService") as mock_service_cls,
        patch("app.api.auth._verify_and_remove_state", return_value=True),
        patch("app.api.auth.limiter") as mock_limiter,
    ):
        mock_limiter.limit.return_value = lambda f: f
        mock_service = mock_service_cls.return_value
        mock_service.handle_google_callback = AsyncMock(
            side_effect=OAuthConfigError("test")
        )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/auth/google/callback?code=fake&state=fake_state",
            follow_redirects=False,
        )
        assert "oauth_not_configured" in response.headers.get("location", "")

    # 일반 Exception → auth_failed
    with (
        patch("app.api.auth.AuthService") as mock_service_cls,
        patch("app.api.auth._verify_and_remove_state", return_value=True),
        patch("app.api.auth.limiter") as mock_limiter,
    ):
        mock_limiter.limit.return_value = lambda f: f
        mock_service = mock_service_cls.return_value
        mock_service.handle_google_callback = AsyncMock(
            side_effect=Exception("some error")
        )

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(
            "/auth/google/callback?code=fake&state=fake_state",
            follow_redirects=False,
        )
        assert "auth_failed" in response.headers.get("location", "")
