from fastapi import APIRouter, Depends, HTTPException, status
import logging
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/applications",
    tags=['Applications']
)

def calculate_application_stats(application, db):
    if not application.firm:
        total_users_for_firm = 0
        total_applications = 0
        successful_applications = 0
        success_rate = 0
    else:
        # Calculate stats as before
        total_users_for_firm = db.query(models.Application.user_id).filter(models.Application.firm == application.firm).distinct().count()
        total_applications = db.query(models.Application).filter(models.Application.firm == application.firm).count()
        successful_applications = db.query(models.Application).filter(models.Application.firm == application.firm, models.Application.outcome == True).count()
        success_rate = (successful_applications / total_applications) * 100 if total_applications > 0 else 0

    return {
        "application": application,
        "summary_stats": {
            "total_users_for_firm": total_users_for_firm,
            "success_rate": success_rate
        }
    }
@router.post("/", response_model=schemas.ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(application_data: schemas.ApplicationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    # Check if an application with the same firm and city for the current user already exists
    existing_application = db.query(models.Application).filter(
        models.Application.user_id == current_user.user_id,
        models.Application.firm == application_data.firm,
        models.Application.city == application_data.city
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An application with the same firm and city already exists."
        )

    new_application = models.Application(user_id=current_user.user_id, **application_data.dict())
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application


@router.get("/me", response_model=List[schemas.ApplicationResponseWithStats], status_code=status.HTTP_200_OK)
async def get_current_user_applications(
        limit: Optional[int] = None,
        current_user: models.User = Depends(oauth2.get_current_user),
        db: Session = Depends(get_db)
):
    logging.info(f"Fetching applications for user: {current_user.user_id}")

    applications_query = db.query(models.Application).filter(models.Application.user_id == current_user.user_id).order_by(models.Application.last_updated.desc())
    if limit is not None:
        applications_query = applications_query.limit(limit)

    applications = applications_query.all()

    applications_with_stats = [calculate_application_stats(application, db) for application in applications]

    logging.info(f"Applications found: {applications_with_stats}")

    if not applications:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No applications found")

    return applications_with_stats

@router.get("/me/{application_id}", response_model=schemas.ApplicationResponseWithStats, status_code=status.HTTP_200_OK)
async def get_specific_application(application_id: int, current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    application = db.query(models.Application).filter(models.Application.user_id == current_user.user_id, models.Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return calculate_application_stats(application, db)

# Endpoint to update a specific application
@router.put("/{application_id}", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def update_application(application_id: int, application_data: schemas.ApplicationUpdate,
                             db: Session = Depends(get_db),
                             current_user: models.User = Depends(oauth2.get_current_user)):
    # Fetch the application to be updated and ensure it belongs to the current user
    application = db.query(models.Application).filter(models.Application.application_id == application_id,
                                                      models.Application.user_id == current_user.user_id).first()

    # If the application does not exist or does not belong to the current user, return an error
    if not application:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    # Update the application with the provided data
    for var, value in vars(application_data).items():
        setattr(application, var, value) if value is not None else None

    db.commit()
    return {"message": "Application updated successfully"}

# Endpoint to delete a specific application
@router.delete("/{application_id}", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def delete_application(application_id: UUID, db: Session = Depends(get_db)):
    application = db.query(models.Application).filter(models.Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    db.delete(application)
    db.commit()
    return {"message": "Application deleted successfully"}