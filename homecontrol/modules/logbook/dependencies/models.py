"""Data models for SQLAlchemy"""
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import Column, DateTime, String

Base = declarative_base()  # pylint: disable=invalid-name


class StateLog(Base):
    """Data model representing a state change"""
    __tablename__ = "states"

    timestamp = Column(DateTime(timezone=True))
    item_identifier = Column(String)
    state_name = Column(String)
    state_value = Column(String)
    state_type = Column(String)
    state_id = Column(String, primary_key=True)

    def dump(self) -> dict:
        """
        Dumps StateLog into a JSON serialisable object
        """
        return {
            "!type": "StateLog",
            "name": self.state_name,
            "value": self.state_value,
            "item": self.item_identifier,
            "state_type": self.state_type,
            "timestamp": self.timestamp
        }


class EventLog(Base):
    """Data model representing an event"""
    __tablename__ = "events"

    timestamp = Column(DateTime(timezone=True))
    event_type = Column(String)
    event_id = Column(String, primary_key=True)

    def dump(self) -> dict:
        """
        Dumps EventLog into a JSON serialisable object
        """
        return {
            "!type": "EventLog",
            "event_type": self.event_type,
            "timestamp": self.timestamp
        }
