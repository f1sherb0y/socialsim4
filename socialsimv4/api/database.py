from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./socialsim.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


Base.metadata.create_all(bind=engine)
