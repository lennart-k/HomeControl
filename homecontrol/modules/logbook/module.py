"""logbook module"""
import logging
from contextlib import contextmanager

import uuid
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import voluptuous as vol
from aiohttp import web

from homecontrol.dependencies.event_engine import Event
from homecontrol.dependencies.entity_types import Item
from homecontrol.dependencies.json import dumps
from homecontrol.dependencies.json_response import JSONResponse
from homecontrol.dependencies.validators import ConsistsOf

import models  # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Required("db-path"): str,
    vol.Required("exclude", default={"items": [], "events": []}): {
        vol.Required("items", default=[]): ConsistsOf(str),
        vol.Required("events", default=[]): ConsistsOf(str)
    }
})


class Module:
    """The logbook module"""
    async def init(self) -> None:
        """Initialise the logbook module"""
        self.cfg = await self.core.cfg.register_domain(
            "state-logs",
            self,
            schema=CONFIG_SCHEMA,
            allow_reload=False
        )
        self.engine = sqlalchemy.create_engine(
            self.cfg["db-path"], strategy="threadlocal")
        models.Base.metadata.create_all(self.engine)

        self.get_session = sessionmaker(bind=self.engine)

        event("state_change")(self.on_state_change)
        event("*")(self.on_event)
        event("http_add_api_routes")(self.add_api_routes)

    @contextmanager
    def session_context(self):
        """A context manager for an SQL session"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e: # pylint: disable=broad-except
            LOGGER.error("An error occured when executing a query: %s", e)
        finally:
            session.close()

    async def on_state_change(self,
                              event: Event,
                              item: Item,
                              changes: dict) -> None:
        """
        Log a state change in the states table
        """

        if item.identifier in self.cfg["exclude"]["items"]:
            return

        with self.session_context() as session:
            for state, value in changes.items():
                state_obj = models.StateLog(
                    timestamp=event.timestamp,
                    item_identifier=item.identifier,
                    state_name=state,
                    state_value=dumps(value),
                    state_type=type(value).__name__,
                    state_id=str(uuid.uuid4())
                )
                session.add(state_obj)

    async def on_event(self,
                       event: Event,
                       **kwargs: dict) -> None:
        """
        Log an event in the events table
        """

        if event.event_type in self.cfg["exclude"]["events"]:
            return

        with self.session_context() as session:
            event_obj = models.EventLog(
                timestamp=event.timestamp,
                event_type=event.event_type,
                event_id=str(uuid.uuid4())
            )
            session.add(event_obj)

    async def add_api_routes(self,
                             event: Event,
                             router: web.RouteTableDef) -> None:
        """
        Add API routes to access the logbook
        """
        @router.get("/logbook/states/{item}")
        async def get_state_log(request: web.Request) -> JSONResponse:
            identifier = request.match_info["item"]
            state_name = request.query.get("state", None)

            with self.session_context() as session:
                result = session.query(models.StateLog).filter(
                    models.StateLog.item_identifier == identifier
                )
                if state_name:
                    result = result.filter(
                        models.StateLog.state_name == state_name
                    )

            return JSONResponse(result.all())

        @router.get("/logbook/events")
        async def get_event_log(request: web.Request) -> JSONResponse:
            with self.session_context() as session:
                result = session.query(models.EventLog)

            return JSONResponse(result.all())

        @router.get("/logbook/events/{type}")
        async def get_event_log_by_type(request: web.Request) -> JSONResponse:
            event_type = request.match_info["type"]

            with self.session_context() as session:
                result = session.query(models.EventLog).filter(
                    models.EventLog.event_type == event_type
                )

            return JSONResponse(result.all())


    async def stop(self) -> None:
        """Stop the logbook module"""
        self.core.event_engine.remove_handler(
            "state_change", self.on_state_change)
        self.core.event_engine.remove_handler(
            "*", self.on_event)
        self.engine.close()
