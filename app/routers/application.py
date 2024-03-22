from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
import logging
import numpy as np
from sqlalchemy import func, extract, or_, and_
from sqlalchemy.orm import Session
from typing import List, Optional
import random

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/applications",
    tags=['Applications']
)


def calculate_recent_responses_and_stage(application, db):
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent_responses_count = 0
    current_stage = application.stage  # Use the outcome directly as the current stage

    # Map the application outcome to the count query
    if application.stage in ["Submitted Application"]:
        recent_responses_count = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            models.Application.applied_response_date >= one_week_ago
        ).count()
    elif application.stage == "Screener Invite":
        recent_responses_count = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            models.Application.screener_response_date >= one_week_ago
        ).count()
    elif application.stage == "Callback Invite":
        recent_responses_count = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            models.Application.callback_response_date >= one_week_ago
        ).count()
    elif application.stage in ["Not Submitted", "Offer"]:
        recent_responses_count = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            or_(
                models.Application.applied_response_date >= one_week_ago,
                models.Application.screener_response_date >= one_week_ago,
                models.Application.callback_response_date >= one_week_ago
            )
        ).count()
    elif application.stage == "Rejection":
        recent_responses_count = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            models.Application.stage == "Rejection"
        ).count()

    return recent_responses_count, current_stage

def calculate_application_stats(application, db):
    if not application.firm:
        summary_stats = {
            "total_users_for_firm": 0,
            "total_applications": 0,
            "successful_applications": 0,
            "success_rate": 0.0,
            "median_responses": {
                "median_applied_to_response": {"success": 0, "not_success": 1},
                "median_screener_to_response": {"success": 0, "not_success": 1},
                "median_callback_to_response": {"success": 0, "not_success": 1},
            },
            "recent_responses_at_current_stage": 0,
            "current_stage": "Firm not specified"
        }
    else:
        total_users_for_firm = db.query(models.Application.user_id).filter(models.Application.firm == application.firm).distinct().count()
        total_applications = db.query(models.Application).filter(models.Application.firm == application.firm).count()
        successful_applications = db.query(models.Application).filter(models.Application.firm == application.firm, models.Application.stage == "Offer").count()
        success_rate = round((successful_applications / total_applications) * 100, 1) if total_applications > 0 else 0

        # Fetch values for calculating medians
        applied_values_success = db.query(models.Application.applied_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.applied_to_response.isnot(None),
            or_(
                models.Application.screener_to_response.isnot(None),
                models.Application.callback_to_response.isnot(None),
                models.Application.stage.in_(["Screener Invite", "Callback Invite", "Offer"])
            )
        ).all()
        applied_values_not_success = db.query(models.Application.applied_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.applied_to_response.isnot(None),
            models.Application.screener_to_response.is_(None),
            models.Application.callback_to_response.is_(None),
            models.Application.stage.in_(["Submitted Application", "Rejection"])
        ).all()

        screener_values_success = db.query(models.Application.screener_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.screener_to_response.isnot(None),
            models.Application.callback_to_response.isnot(None),
            models.Application.stage.in_(["Callback Invite", "Offer"])
        ).all()
        screener_values_not_success = db.query(models.Application.screener_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.screener_to_response.isnot(None),
            models.Application.callback_to_response.is_(None),
            models.Application.stage.in_(["Screener Invite", "Rejection"])
        ).all()

        callback_values_success = db.query(models.Application.callback_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.callback_to_response.isnot(None),
            models.Application.stage.in_(["Callback Invite", "Offer"])
        ).all()
        callback_values_not_success = db.query(models.Application.callback_to_response).filter(
            models.Application.firm == application.firm,
            models.Application.callback_to_response.isnot(None),
            models.Application.stage == "Rejection"
        ).all()

        # Calculate medians
        median_applied_to_response_success = calculate_median([value for value, in applied_values_success])
        median_applied_to_response_not_success = calculate_median([value for value, in applied_values_not_success])
        median_screener_to_response_success = calculate_median([value for value, in screener_values_success])
        median_screener_to_response_not_success = calculate_median([value for value, in screener_values_not_success])
        median_callback_to_response_success = calculate_median([value for value, in callback_values_success])
        median_callback_to_response_not_success = calculate_median([value for value, in callback_values_not_success])

        summary_stats = {
            "total_users_for_firm": total_users_for_firm,
            "total_applications": total_applications,
            "successful_applications": successful_applications,
            "success_rate": success_rate,
            "recent_responses_at_current_stage": calculate_recent_responses_and_stage(application, db)[0],
            "median_responses": {
                "median_applied_to_response": {"success": median_applied_to_response_success, "not_success": median_applied_to_response_not_success},
                "median_screener_to_response": {"success": median_screener_to_response_success, "not_success": median_screener_to_response_not_success},
                "median_callback_to_response": {"success": median_callback_to_response_success, "not_success": median_callback_to_response_not_success},
            },
            "current_stage": application.stage
        }

        applications_with_screener = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            or_(
                models.Application.stage.in_(["Screener Invite", "Callback Invite", "Offer"]),
                and_(
                    models.Application.stage == "Rejection",
                    or_(
                        models.Application.screener_to_response.isnot(None),
                        models.Application.callback_to_response.isnot(None)
                    )
                )
            )
        ).count()
        applications_with_callback = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            or_(
                models.Application.stage.in_(["Callback Invite", "Offer"]),
                and_(
                    models.Application.stage == "Rejection",
                    models.Application.callback_to_response.isnot(None)
                )
            )
        ).count()
        applications_with_offer = db.query(models.Application).filter(
            models.Application.firm == application.firm,
            models.Application.stage == "Offer"
        ).count()

        # Calculate rates
        application_to_screener_rate = {
            "rate": round((applications_with_screener / total_applications) * 100, 1) if total_applications > 0 else 0,
            "numerator": applications_with_screener,
            "denominator": total_applications
        }
        screener_to_callback_rate = {
            "rate": round((applications_with_callback / applications_with_screener) * 100,
                          1) if applications_with_screener > 0 else 0,
            "numerator": applications_with_callback,
            "denominator": applications_with_screener
        }
        callback_to_offer_rate = {
            "rate": round((applications_with_offer / applications_with_callback) * 100,
                          1) if applications_with_callback > 0 else 0,
            "numerator": applications_with_offer,
            "denominator": applications_with_callback
        }

        # Update summary_stats with success_rate_granular
        summary_stats.update({
            "success_rate_granular": {
                "application_to_screener_rate": application_to_screener_rate,
                "screener_to_callback_rate": screener_to_callback_rate,
                "callback_to_offer_rate": callback_to_offer_rate
            }
        })

        # Fetching the earliest start dates for each stage without year constraint
        screener_start_date = db.query(func.min(models.Application.screener_date)).filter(
            models.Application.firm == application.firm
        ).scalar()

        callback_start_date = db.query(func.min(models.Application.callback_date)).filter(
            models.Application.firm == application.firm
        ).scalar()

        offer_start_date = db.query(func.min(models.Application.callback_response_date)).filter(
            models.Application.firm == application.firm,
            models.Application.stage == "Offer"
        ).scalar()

        # Incorporating the new start date fields into the summary_stats
        summary_stats.update({
            "start_dates": {
                "screener_start": screener_start_date,
                "callback_start": callback_start_date,
                "offer_start": offer_start_date
            }
        })

        # The rest of your existing logic...
        return {
            "application": application,
            "summary_stats": summary_stats
        }





def calculate_median(values):
    """Calculate the median of a list of values, with a default of 1 if empty or median is 0."""
    if not values:
        return 1
    median_value = np.median(np.array(values))
    return median_value if median_value != 0 else 1


@router.post("/", response_model=schemas.ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(application_data: schemas.ApplicationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    # Generate a random 10-digit number for application_id
    random_application_id = random.randint(100000000, 2147483647)

    # Check if an application with the generated ID already exists to ensure uniqueness
    existing_application = db.query(models.Application).filter(models.Application.application_id == random_application_id).first()
    while existing_application is not None:
        random_application_id = random.randint(100000000, 2147483647)
        existing_application = db.query(models.Application).filter(models.Application.application_id == random_application_id).first()

    # Proceed with creating a new application using the unique random_application_id
    new_application = models.Application(
        application_id=random_application_id,
        user_id=current_user.user_id,
        **application_data.dict()
    )

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

    # Modify the query to filter out applications where firm is null
    applications_query = db.query(models.Application).filter(
        models.Application.user_id == current_user.user_id,
        models.Application.firm.isnot(None)
    ).order_by(models.Application.last_updated.desc())

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
@router.put("/{application_id}", response_model=schemas.ApplicationResponseWithStats, status_code=status.HTTP_200_OK)
async def update_application(application_id: int, application_data: schemas.ApplicationUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
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

    updated_application_stats = calculate_application_stats(application, db)
    return updated_application_stats

# Endpoint to delete a specific application
@router.delete("/{application_id}", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(models.Application).filter(models.Application.application_id == application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    db.delete(application)
    db.commit()
    return {"message": "Application deleted successfully"}

@router.get("/total", status_code=status.HTTP_200_OK)
def get_total_applications(db: Session = Depends(get_db)):
    total_applications = db.query(models.Application).filter(models.Application.firm.isnot(None)).count()
    total_users = db.query(models.Application.user_id).distinct().count()
    return {
        "total_applications": total_applications,
        "total_users": total_users
    }