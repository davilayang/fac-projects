import logging
import secrets

from pathlib import Path
from urllib.parse import urlencode

import requests as http

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from arxiv_rag.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_STATIC_DIR = Path(__file__).parent.parent / "static"

COOKIE_NAME = "arxiv_rag_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
GITHUB_ORG_MEMBER_URL = "https://api.github.com/orgs/{org}/members/{username}"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret.get_secret_value())


def make_session_cookie(login: str, email: str) -> str:
    return _serializer().dumps({"login": login, "email": email})


def read_session_cookie(value: str) -> dict | None:
    try:
        return _serializer().loads(value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/login", include_in_schema=False, response_model=None)
def login_page(request: Request, error: str = "") -> HTMLResponse | RedirectResponse:
    """Serve the login page. Redirect home if already authenticated."""
    cookie = request.cookies.get(COOKIE_NAME, "")
    if cookie and read_session_cookie(cookie):
        return RedirectResponse(url="/")
    return HTMLResponse(content=(_STATIC_DIR / "login.html").read_text())


@router.get("/oauth", include_in_schema=False)
def oauth_redirect() -> RedirectResponse:
    """Initiate the GitHub OAuth flow."""
    settings = get_settings()
    state = secrets.token_urlsafe(16)
    scope = "read:user user:email" + (
        " read:org" if settings.allowed_github_org else ""
    )
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "scope": scope,
            "state": state,
        }
    )
    response = RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{params}")
    response.set_cookie(
        "oauth_state",
        state,
        max_age=300,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/callback", include_in_schema=False)
def callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
) -> RedirectResponse:
    """Handle GitHub OAuth callback."""
    settings = get_settings()

    if error:
        logger.warning("GitHub OAuth denied: %s", error)
        return RedirectResponse(url="/auth/login?error=oauth_denied")

    stored_state = request.cookies.get("oauth_state", "")
    if not state or state != stored_state:
        logger.warning("OAuth state mismatch")
        return RedirectResponse(url="/auth/login?error=state_mismatch")

    # Exchange code → access token
    token_resp = http.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret.get_secret_value(),
            "code": code,
        },
        timeout=10,
    )
    access_token = token_resp.json().get("access_token", "")
    if not access_token:
        logger.error("No access_token in GitHub response: %s", token_resp.text)
        return RedirectResponse(url="/auth/login?error=token_exchange_failed")

    gh = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    # Fetch verified emails
    emails_data = http.get(GITHUB_EMAILS_URL, headers=gh, timeout=10).json()
    verified_emails = {e["email"].lower() for e in emails_data if e.get("verified")}
    primary_email = next(
        (
            e["email"].lower()
            for e in emails_data
            if e.get("primary") and e.get("verified")
        ),
        next(iter(verified_emails), ""),
    )

    # Fetch GitHub login
    user_data = http.get(GITHUB_USER_URL, headers=gh, timeout=10).json()
    github_login = user_data.get("login", "")

    # Authorization: email allowlist
    allowed = settings.allowed_emails_set
    if allowed and not (allowed & verified_emails):
        logger.warning(
            "Login blocked — email not in allowlist: %s (verified emails on GitHub: %s)",
            github_login,
        )
        return RedirectResponse(url="/auth/login?error=not_allowed")

    # Authorization: org membership
    if settings.allowed_github_org:
        url = GITHUB_ORG_MEMBER_URL.format(
            org=settings.allowed_github_org, username=github_login
        )
        member_resp = http.get(url, headers=gh, timeout=10)
        if member_resp.status_code != 204:
            logger.warning(
                "Login blocked — not a member of org %s: %s",
                settings.allowed_github_org,
                github_login,
            )
            return RedirectResponse(url="/auth/login?error=not_allowed")

    # Set signed session cookie and redirect home
    response = RedirectResponse(url="/")
    response.set_cookie(
        COOKIE_NAME,
        make_session_cookie(github_login, primary_email),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.delete_cookie("oauth_state")
    logger.info("Login successful: %s (%s)", github_login, primary_email)
    return response


@router.get("/logout", include_in_schema=False)
def logout() -> RedirectResponse:
    settings = get_settings()
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie(COOKIE_NAME, secure=settings.cookie_secure, samesite="lax")
    return response


@router.get("/me")
def me(request: Request) -> JSONResponse:
    """Return current session info for the UI header chip."""
    session = getattr(request.state, "session", None)
    if session:
        return JSONResponse(
            {"login": session.get("login"), "email": session.get("email", "")}
        )
    return JSONResponse({"login": None})
