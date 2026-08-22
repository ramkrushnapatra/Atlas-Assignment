import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from reconciliation.db.models import Base

DB_PATH = Path(__file__).parent.parent.parent / "reconciliation.db"
engine = create_engine(os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}"), echo=False)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
  Base.metadata.create_all(bind=engine)


def get_session():
  return Session()
