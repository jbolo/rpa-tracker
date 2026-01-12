import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rpa_tracker.models.tx_process import Base as ProcessBase
from rpa_tracker.models.tx_stage import Base as StageBase
from rpa_tracker.models.tx_event import Base as EventBase


@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:")
    ProcessBase.metadata.create_all(engine)
    StageBase.metadata.create_all(engine)
    EventBase.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
