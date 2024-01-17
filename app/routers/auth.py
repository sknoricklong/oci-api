from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from .. import models, schemas, utils, oauth2
from ..database import get_db
from ..utils import verify_password

router = APIRouter(
    tags=['Authentication']
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post('/login', response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user or not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = oauth2.create_access_token(data={"sub": str(user.user_id)})
    return {"access_token": token, "token_type": "bearer"}
