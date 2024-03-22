from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    database_host: str
    database_port: str
    database_name: str
    database_username: str
    database_password: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    port: str
    google_client_id: str
    google_client_secret: str
    url: str
    google_password: str

    class Config:
        env_file = '.env'


settings = Settings()