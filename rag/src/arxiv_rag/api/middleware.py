from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from arxiv_rag.log import new_trace_id

_PUBLIC_PATHS = {"/health", "/auth/login", "/auth/oauth", "/auth/callback"}
_PUBLIC_PREFIXES = ("/static/",)


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        new_trace_id()
        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        from arxiv_rag.api.routes.auth import COOKIE_NAME, read_session_cookie

        path = request.url.path

        if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        if cookie:
            session = read_session_cookie(cookie)
            if session:
                request.state.session = session
                return await call_next(request)

        # API routes → 401 JSON (keeps SSE fetch from silently redirecting)
        if path.startswith("/apis/") or path.startswith("/auth/me"):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        return RedirectResponse(url="/auth/login")
