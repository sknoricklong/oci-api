from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .config import settings
from .database import engine
from .routers import user, auth, profile, application


# models.Base.metadata.create_all(bind=engine)

# Set up CORS middleware options
origins = [
    "https://www.nytimes.com",
    "https://www.google.com/"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(application.router)


@app.get("/")
async def root():
    return {"message": "Hello world"}
