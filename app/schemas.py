from datetime import date, datetime
from pydantic import BaseModel, validator, EmailStr, Field
from sqlalchemy import func
from typing import List, Optional, Dict
import uuid

from .loader import load_law_schools, load_cities

law_schools = load_law_schools()['School'].tolist()
cities = load_cities()

class UserBase(BaseModel):
    email: EmailStr
    password: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = False

class User(UserBase):
    user_id: str = None
    created_at: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.user_id:
            self.user_id = str(uuid.uuid4())

class UserResponse(BaseModel):
    email: EmailStr
    user_id: uuid.UUID
    created_at: datetime
    is_active: Optional[bool] = False

class MessageResponse(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

class ProfileBase(BaseModel):
    school: Optional[str] = None
    rank: Optional[int] = None
    circumstances: Optional[List[str]] = None
    last_updated: Optional[datetime] = None

    @validator('school', pre=True, allow_reuse=True)
    def validate_school(cls, value):
        if value is not None and value not in law_schools:
            raise ValueError(f'School "{value}" is not in the list of law schools')
        return value

    def update_last_updated(self):
        self.last_updated = datetime.now()

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    circumstances: Optional[List[str]] = None

class ProfileResponse(ProfileBase):
    user: UserResponse


class ApplicationBase(BaseModel):
    firm: Optional[str] = None
    city: Optional[str] = None
    networked: Optional[List[str]] = None
    applied_date: Optional[date] = None
    applied_response_date: Optional[date] = None
    applied_to_response: Optional[int] = None
    screener_date: Optional[date] = None
    screener_response_date: Optional[date] = None
    screener_to_response: Optional[int] = None
    callback_date: Optional[date] = None
    callback_response_date: Optional[date] = None
    callback_to_response: Optional[int] = None
    stage: Optional[str] = "Not Submitted"
    last_updated: Optional[datetime] = None

    @validator('applied_date', 'applied_response_date', 'screener_date', 'screener_response_date', 'callback_date',
               'callback_response_date', pre=True)
    def parse_and_validate_date(cls, value):
        if isinstance(value, str):
            try:
                parsed_date = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Invalid date format for {value}. Expected format: YYYY-MM-DD.")
        else:
            parsed_date = value

        if parsed_date and parsed_date.year != 2024:
            raise ValueError('Date must be in the year 2024')
        return parsed_date

    @validator('city', pre=True, allow_reuse=True)
    def validate_city(cls, value):
        if value is None:
            return value
        if value not in cities:
            raise ValueError(f'City "{value}" is not in the list of valid cities')
        return value

def update_last_updated(self):
        self.last_updated = datetime.now()

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    application_id: int
    user_id: uuid.UUID
    last_updated: Optional[datetime] = None

class MedianResponse(BaseModel):
    success: Optional[float] = Field(None, description="Median days for successful response")
    not_success: Optional[float] = Field(None, description="Median days for unsuccessful response")

class GranularRate(BaseModel):
    rate: float
    numerator: int
    denominator: int

class SuccessRateGranular(BaseModel):
    application_to_screener_rate: GranularRate
    screener_to_callback_rate: GranularRate
    callback_to_offer_rate: GranularRate

class StartDates(BaseModel):
    screener_start: Optional[date] = None
    callback_start: Optional[date] = None
    offer_start: Optional[date] = None

class SummaryStats(BaseModel):
    total_users_for_firm: int
    total_applications: int
    successful_applications: int
    success_rate: float
    recent_responses_at_current_stage: int
    median_responses: Dict[str, MedianResponse]
    current_stage: str
    success_rate_granular: SuccessRateGranular
    start_dates: StartDates

class ApplicationResponseWithStats(BaseModel):
    application: ApplicationResponse
    summary_stats: SummaryStats

class ApplicationResponseWithStats(BaseModel):
    application: ApplicationResponse
    summary_stats: SummaryStats

