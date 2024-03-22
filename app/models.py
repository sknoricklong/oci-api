from sqlalchemy import ARRAY, Boolean, Column, Date, String, DateTime, Integer, ForeignKey, func, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from sqlalchemy.event import listens_for
import uuid
from .database import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.timezone('UTC', func.now()))
    is_active = Column(Boolean, default=False)

    # Setup cascade delete
    profile = relationship("Profile", uselist=False, backref="user", cascade="all, delete, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")



    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}')>"


class Profile(Base):
    __tablename__ = 'profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    school = Column(String, nullable=True)
    rank = Column(Integer, nullable=True)
    circumstances = Column(ARRAY(String), nullable=True)
    last_updated = Column(DateTime, nullable=True, default=func.timezone('UTC', func.now()), onupdate=func.timezone('UTC', func.now()))

    def __repr__(self):
        return f"<Profile(user_id='{self.user_id}', school='{self.school}', rank='{self.rank}', circumstances='{self.circumstances}', last_updated='{self.last_updated}')>"


@listens_for(User, 'after_insert')
def create_user_profile(mapper, connection, target):
    new_profile = Profile(user_id=target.user_id)
    connection.execute(
        Profile.__table__.insert(),
        {"user_id": new_profile.user_id}
    )

@listens_for(User, 'after_insert')
def create_initial_application(mapper, connection, target):
    new_application = Application(user_id=target.user_id)
    connection.execute(
        Application.__table__.insert(),
        {
            "user_id": new_application.user_id,
            # Set default or null values for other fields if required
        }
    )

class Application(Base):
    __tablename__ = 'applications'

    application_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'))
    firm = Column(String, nullable=True)
    city = Column(String, nullable=True)
    networked = Column(ARRAY(String), nullable=True)  # Junior, Senior, Reception
    applied_date = Column(Date, nullable=True)
    applied_response_date = Column(Date, nullable=True)
    applied_to_response = Column(Integer, nullable=True)
    screener_date = Column(Date, nullable=True)
    screener_response_date = Column(Date, nullable=True)
    screener_to_response = Column(Integer, nullable=True)
    callback_date = Column(Date, nullable=True)
    callback_response_date = Column(Date, nullable=True)
    callback_to_response = Column(Integer, nullable=True)
    stage = Column(String, nullable=True, default="Not Submitted")
    last_updated = Column(DateTime, nullable=True, default=func.now(), onupdate=func.now())

    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="applications")

    __table_args__ = (UniqueConstraint('user_id', 'firm', 'city', name='_user_firm_city_uc'),)