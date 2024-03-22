import bcrypt
import httpx
from sqlalchemy.orm import Session
from .config import settings
from . import models

BASE_URL = f'{settings.url}:{settings.port}'

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_user_by_email(email: str, db: Session) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def send_http_request(endpoint: str, method: str, data: dict = None, token: str = None):
    url = f"{BASE_URL}{endpoint}"  # Construct the full URL
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    async with httpx.AsyncClient() as client:
        if method.upper() == 'POST':
            response = await client.post(url, json=data, headers=headers)
        elif method.upper() == 'PUT':
            response = await client.put(url, json=data, headers=headers)
        elif method.upper() == 'GET':
            response = await client.get(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        return response