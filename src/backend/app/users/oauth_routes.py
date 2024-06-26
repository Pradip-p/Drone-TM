import os
import json
from loguru import logger as log
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import database
from app.users.user_routes import router
from app.users.user_deps import init_google_auth, login_required
from app.users.user_schemas import AuthUser
from app.config import settings

if settings.DEBUG:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


@router.get("/google-login")
async def login_url(google_auth=Depends(init_google_auth)):
    """Get Login URL for Google Oauth Application.

    The application must be registered on google oauth.
    Open the download url returned to get access_token.

    Args:
        request: The GET request.
        google_auth: The Auth object.

    Returns:
        login_url (string): URL to authorize user in Google OAuth.
            Includes URL params: client_id, redirect_uri, permission scope.
    """
    login_url = google_auth.login()
    log.debug(f"Login URL returned: {login_url}")
    return JSONResponse(content=login_url, status_code=200)


@router.get("/callback/")
async def callback(request: Request, google_auth=Depends(init_google_auth)):
    """Performs token exchange between Google and DTM API"""

    callback_url = str(request.url)
    access_token = google_auth.callback(callback_url).get("access_token")
    return json.loads(access_token)


@router.get("/my-info/")
async def my_data(
    db: Session = Depends(database.get_db),
    user_data: AuthUser = Depends(login_required),
):
    """Read access token and get user details from Google"""

    return user_data