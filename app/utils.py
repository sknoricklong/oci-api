import bcrypt
import jwt
from sqlalchemy.orm import Session

from . import models

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_user_by_email(email: str, db: Session) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

