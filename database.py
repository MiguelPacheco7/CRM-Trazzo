from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

SQLALCHEMY_DATABASE_URL = "sqlite:///./crm.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    company = Column(String)
    social_media = Column(String)
    phone = Column(String)
    status = Column(String)  # Lead, Negociação, Não fechou, Fechado
    temperature = Column(String)  # Quente, Morno, Frio
    problems = Column(Text)
    solutions = Column(Text)
    observations = Column(Text)
    value = Column(Float, default=0.0)
    project_type = Column(String)
    photo_path = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    company = Column(String)
    social_media = Column(String)
    phone = Column(String)
    project_type = Column(String) # Marca autêntica, Posicionamento, Consultoria
    value = Column(Float)
    start_date = Column(DateTime, default=utc_now)
    end_date = Column(DateTime)
    scope = Column(Text)
    observations = Column(Text)
    photo_path = Column(String, nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

Base.metadata.create_all(bind=engine)
