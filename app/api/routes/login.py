from datetime import timedelta
from typing import Annotated

from app.api.deps import SessionDep
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.db_model import Token
from app.db_option import get_user_by_email
from app.security import verify_password, create_access_token
from app.settings import settings

router = APIRouter(prefix="/login", tags=["login"])


@router.post("/token")
def login_token(
        session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    认证token
    :param session:
    :param form_data:
    :return:
    """
    db_user = get_user_by_email(session=session, email=form_data.username)
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not verify_password(plain_password=form_data.password, hashed_password=db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=create_access_token(
            db_user.id, expires_delta=access_token_expires
        )
    )
