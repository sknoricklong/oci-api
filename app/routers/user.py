from fastapi import Depends, HTTPException, status, APIRouter
import sqlalchemy
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db
from ..utils import hash_password, get_user_by_email


router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.put('/me', response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def update_user_me(update_data: schemas.UserUpdate, db: Session = Depends(get_db),
                      current_user: models.User = Depends(oauth2.get_current_user)):

    if update_data.email is not None:
        current_user.email = update_data.email
    if update_data.password is not None:
        current_user.password = hash_password(update_data.password)

    db.commit()

    return schemas.MessageResponse(message="User updated successfully")


@router.get("/me", response_model=schemas.UserResponse, status_code=status.HTTP_200_OK)
async def get_user(current_user: models.User = Depends(oauth2.get_current_user)):
    return schemas.UserResponse(
        email=current_user.email,
        user_id=str(current_user.user_id),
        created_at=current_user.created_at
    )

@router.delete('/me', response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def delete_user(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    # Delete the current user
    db.delete(current_user)
    db.commit()

    return schemas.MessageResponse(message="User account deleted successfully")

@router.post('/', response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(user_data.email, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    new_user_data = user_data.dict()
    new_user_data['password'] = hash_password(user_data.password)

    new_user = models.User(**new_user_data)
    db.add(new_user)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError as e:
        print(e)  # Log the exception details
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the user."
        ) from e

    db.refresh(new_user)
    return schemas.UserResponse(
        email=new_user.email,
        user_id=str(new_user.user_id),
        created_at=new_user.created_at
    )



# @router.put('/{user_id}', response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
# async def update_user(user_id: UUID, update_data: schemas.UserUpdate, db: Session = Depends(get_db),
#                       current_user: models.User = Depends(oauth2.get_current_user)):
#     if str(current_user.user_id) != user_id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user.")
#
#     user = db.query(models.User).filter(models.User.user_id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#
#     if update_data.email is not None:
#         user.email = update_data.email
#     if update_data.password is not None:
#         user.password = hash_password(update_data.password)
#
#     db.commit()
#
#     return schemas.MessageResponse(message="User updated successfully")
#
# @router.get("/{user_id}", response_model=schemas.UserResponse, status_code=status.HTTP_200_OK)
# async def get_user(user_id: UUID, db: Session = Depends(get_db),
#                    current_user: models.User = Depends(oauth2.get_current_user)):
#
#     if str(current_user.user_id) != user_id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this user.")
#
#     user = db.query(models.User).filter(models.User.user_id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#
#     return schemas.UserResponse(
#         email=user.email,
#         user_id=str(user.user_id),
#         created_at=user.created_at
#     )
#
#
# @router.delete('/{user_id}', response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
# async def delete_user(user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
#     if str(current_user.user_id) != user_id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user.")
#
#     user = db.query(models.User).filter(models.User.user_id == user_id).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
#
#     db.delete(user)
#     db.commit()
#
#     return schemas.MessageResponse(message=f"User with id {user_id} deleted successfully")



