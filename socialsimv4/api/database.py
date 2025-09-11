from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./socialsim.db"

engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class SimulationTemplate(Base):
    __tablename__ = "simulation_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    template_json = Column(Text)
    owner_id = Column(Integer)


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    usage = Column(String)
    kind = Column(String)
    base_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    model = Column(String, nullable=True)
    temperature = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    top_p = Column(Integer, nullable=True)
    frequency_penalty = Column(Integer, nullable=True)
    presence_penalty = Column(Integer, nullable=True)
    stream = Column(Integer, nullable=True)


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
