from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, ForeignKey, MetaData, JSON, create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os
from fastapi import Depends

# Create SQLAlchemy engine and session
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/appdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

metadata = MetaData()

agent_templates = Table(
    'agent_templates',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False),
    Column('type', String, nullable=False),
    Column('description', String),
    Column('config', JSON, default={}),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

repositories = Table(
    'repositories',
    metadata,
    Column('id', String, primary_key=True),
    Column('name', String, nullable=False),
    Column('url', String, nullable=False),
    Column('api_url', String),
    Column('description', String),
    Column('type', String),
    Column('branch', String),
    Column('auth_type', String),
    Column('auth_config', JSON),
    Column('owner', String, nullable=False),
    Column('is_active', Boolean, default=True),
    Column('last_sync_status', String),
    Column('last_sync_at', DateTime),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column('is_public', Boolean, default=False)
)

projects = Table(
    'projects',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False),
    Column('description', String),
    Column('repository_id', Integer, ForeignKey('repositories.id', ondelete='SET NULL')),
    Column('repository_url', String),
    Column('repository_owner', String),
    Column('repository_name', String),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

project_agents = Table(
    'project_agents',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('project_id', String, nullable=False),
    Column('agent_template_id', Integer, nullable=False),
    Column('name', String, nullable=False),
    Column('type', String, nullable=False),
    Column('description', String),
    Column('config', String, default='{}'),
    Column('step_key', String),  # SDLC step this agent is assigned to
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)