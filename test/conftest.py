"""Fixtures for setting up the database session for tests."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rpa_tracker.models.tx_process import Base as ProcessBase
from rpa_tracker.models.tx_stage import Base as StageBase
from rpa_tracker.models.tx_event import Base as EventBase
from test.infra.models.tx_data import Base as DataBase


@pytest.fixture(scope="function")
def session():
    """Provides a SQLAlchemy session connected to an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    DataBase.metadata.create_all(engine)
    ProcessBase.metadata.create_all(engine)
    StageBase.metadata.create_all(engine)
    EventBase.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
