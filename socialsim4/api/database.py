from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from socialsim4.api import config

connect_args = {}
if config.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(config.DATABASE_URL, connect_args=connect_args)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, index=True)
    institution = Column(String, index=True)
    hashed_password = Column(String)
    registration_time = Column(DateTime(timezone=True), server_default=func.now())
    disabled = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_sso = Column(Boolean, default=False)


class SimulationTemplate(Base):
    __tablename__ = "simulation_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    template_json = Column(Text)
    owner_id = Column(Integer, nullable=True)  # Nullable for public templates
    is_public = Column(Boolean, default=False)


class Provider(Base):
    __tablename__ = "providers"

    username = Column(String(50), ForeignKey("users.username"), primary_key=True)
    usage = Column(String(50), primary_key=True)
    kind = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    api_key = Column(String(100), nullable=False)
    base_url = Column(String(200))
    temperature = Column(Float, default=1.0)
    max_tokens = Column(Integer, default=4096)
    top_p = Column(Float, default=0.7)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    stream = Column(Boolean, default=False)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, index=True)
    feedback_text = Column(Text)
    timestamp = Column(String)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session
