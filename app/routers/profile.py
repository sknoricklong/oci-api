from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/profiles",
    tags=['Profiles']
)

# Endpoint to retrieve the profile of the current user
@router.get("/me", response_model=schemas.ProfileResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile

# Endpoint to update the profile of the current user
@router.put("/me", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def update_current_user_profile(profile_data: schemas.ProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    profile = db.query(models.Profile).filter(models.Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Update profile details
    if profile_data.school is not None:
        profile.school = profile_data.school
    if profile_data.rank is not None:
        profile.rank = profile_data.rank
    if profile_data.circumstances is not None:
        profile.circumstances = profile_data.circumstances

    profile.last_updated = datetime.utcnow()  # Manually update the last_updated field
    db.commit()
    return schemas.MessageResponse(message="Profile updated successfully")


