# Copyright (c) 2023 ux-dom
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""web_io adapter internals. Private transport helpers; not a public app API."""
import asyncio
import json
from abc import ABC, abstractmethod
from asyncio import create_task, gather, sleep
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import Any, Optional, Type

from ux_dom.web_io._events import WebSocketEvents
from ux_dom.web_io._protocol import WebSocketProtocol as WebSocket
from ux_dom.web_io._types import MESSAGE


async def _run_handlers(handlers):
    """Run handler coroutines; no-op if empty (asyncio.wait([]) raises)."""
    tasks = list(handlers)
    if not tasks:
        return
    await gather(*tasks)


__all__ = ["WebSocketAdapter", "WebSocketClientHandler", "DataFetcher"]


class GenericAdapter(ABC):
    connections: set

    @abstractmethod
    async def sleep(self):
        pass

    @abstractmethod
    async def connect(self, websocket: WebSocket):
        pass

    @abstractmethod
    async def on_connect(self, *args, websocket: WebSocket, **kwargs):
        pass

    @abstractmethod
    async def disconnect(self, websocket: WebSocket):
        pass

    @abstractmethod
    async def on_disconnect(
        self, *args, websocket: WebSocket, message: Optional[MESSAGE], **kwargs
    ):
        pass

    @abstractmethod
    async def receive(self, websocket: WebSocket) -> MESSAGE:
        pass

    @abstractmethod
    async def on_receive(self, *args, websocket: WebSocket, message: MESSAGE, **kwargs):
        pass

    @abstractmethod
    async def on_relay(
        self,
        *args,
        websocket: WebSocket,
        message: MESSAGE,
        connections: Optional[set[WebSocket]] = None,
        **kwargs,
    ):
        pass

    async def __call__(self, *args, **kwargs):
        pass


class DataFetcher:
    def __init__(self, data_class: type):
        self.data_class = data_class

    async def fetch(self, *args, **kwargs) -> Any:
        raise NotImplementedError


class WebSocketAdapter(GenericAdapter):
    """
    A WebSocket adapter that handles stateful communication with a data class instance.

    Attributes:
        class_def (type): The class of the data object to be instantiated.
        events (dict): A mapping of event names to the corresponding method names in the data class.
        data_fetcher (DataFetcher, optional): A data fetcher object to retrieve data from a data store.
                                               Defaults to None, in which case a new instance of the data_class is used.
        class_instance (Any): The instance of the class_def to be used in stateful communication.
    """

    def __init__(
        self,
        data_class: type,
        events: WebSocketEvents,
        data_fetcher: Optional[DataFetcher] = None,
        *,
        share_instance: bool = False,
    ):
        """
        Args:
            share_instance: **Breaking default False (0.5).**
                When False (recommended), each WebSocket connection gets its own
                ``data_class`` instance — no cross-user state leak.
                Set True only for intentionally shared process-wide state
                (shared-instance mode).
        """
        self.data_class: Type = data_class
        self.events: WebSocketEvents = events
        self.data_fetcher: Optional[DataFetcher] = data_fetcher
        self.share_instance: bool = share_instance
        # Shared instance when share_instance=True
        self._shared_instance: Any = None
        # Per-connection instances
        self._instances: dict = {}
        self.connections: set = set()

    def _instance_for(self, websocket: Optional[WebSocket] = None) -> Any:
        if self.share_instance:
            return self._shared_instance
        if websocket is None:
            return None
        return self._instances.get(id(websocket))

    @property
    def class_instance(self) -> Any:
        """Shared instance, or None when using per-connection mode."""
        if self.share_instance:
            return self._shared_instance
        # Prefer any single live instance for naive introspection
        if len(self._instances) == 1:
            return next(iter(self._instances.values()))
        return None

    @class_instance.setter
    def class_instance(self, value: Any) -> None:
        if self.share_instance:
            self._shared_instance = value

    async def sleep(self, time: float = 0.2):
        await sleep(time)

    async def send(self, websocket: WebSocket, response: dict):
        await websocket.send_json(response)

    async def connect(self, websocket: WebSocket):
        # Accept the WebSocket connection.
        await websocket.accept()

    async def on_connect(self, *args, websocket: WebSocket, **kwargs):
        """
        Callback function called on WebSocket connection.

        Args:
            websocket (WebSocket): The WebSocket instance.
        """
        await self.connect(websocket)

        if self.events.connect_events:
            await _run_handlers(
                asyncio.create_task(
                    on_connect_handler(self._instance_for(websocket), websocket)
                )
                for on_connect_handler_list in self.events.connect_events.values()
                for on_connect_handler in on_connect_handler_list
            )

        # Send an "initialize" event with the initial state of the data object.
        # response = {"event": "initialize", "data": self.class_instance.to_dict()}
        # await self.send(websocket, response)

    async def disconnect(self, websocket: WebSocket):
        # Close the WebSocket connection.
        await websocket.close()

    async def on_disconnect(
        self, *args, websocket: WebSocket, message: Optional[MESSAGE], **kwargs
    ):
        """
        Callback function called on WebSocket disconnection.

        Args:
            websocket (WebSocket): The WebSocket instance.
        """
        # Call the `on_disconnect` handlers of the data object, if it exists.
        if self.events.disconnect_events:
            await _run_handlers(
                asyncio.create_task(
                    on_disconnect_handler(
                        self._instance_for(websocket), websocket, message
                    )
                )
                for on_disconnect_handler_list in self.events.disconnect_events.values()
                for on_disconnect_handler in on_disconnect_handler_list
            )
        # await self.disconnect(websocket)

    async def receive(self, websocket: WebSocket) -> MESSAGE:
        # Receive the WebSocket message.
        message = await websocket.receive()
        if "text" in message:
            payload = message["text"]
        elif "bytes" in message:
            payload = message["bytes"]
        else:
            # disconnect / other control frames
            return message  # type: ignore[return-value]

        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                # Non-UTF8 binary frames — keep as bytes (caller may ignore)
                return payload  # type: ignore[return-value]
            try:
                payload = json.loads(payload)
            except JSONDecodeError:
                pass
        elif isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except JSONDecodeError:
                pass
        return payload  # type: ignore[return-value]

    async def on_receive(self, *args, websocket: WebSocket, message: MESSAGE, **kwargs):
        """
        Callback function called on receiving a message over the WebSocket.

        Args:
            websocket (WebSocket): The WebSocket instance.
            data (dict): The message data, with an "event" key indicating the event name and any additional parameters.
        """

        if isinstance(message, dict):
            if "data" in message and "event" not in message:
                # Malformed client payload — ignore (was KeyError → dropped connection)
                return

            if "event" in message:
                if message["event"] in self.events.receive_events:
                    # Get the event name from the received data and corresponding event_handlers from event manager.
                    # If an event handler exists for the given event in data, call the corresponding event_handler
                    # methods passing the class_instance in place of self in event handler
                    await _run_handlers(
                        asyncio.create_task(
                            on_receive_handler(
                                self._instance_for(websocket), websocket, message
                            )
                        )
                        for on_receive_handler in self.events.receive_events[
                            message["event"]
                        ]
                    )
                    # Component data classes can have any methods decorated
                    # eg: event_handler = EventManager()
                    # with EvenManager instance @event_handler.on
                    #
                    # @event_handler.on_receive("some_event")
                    # def some_method(self, websocket, data): <-- here in place of 'self' we pass self.class_instance
                    # # Send an "update" event with the updated state of the data object.
                    # response = {
                    #     "event": "update",
                    #     "data": self.class_instance.to_dict(),
                    # }
                    # await self.sleep()
                    # await self.send(websocket, response)

    async def on_relay(self, *args, websocket, message, **kwargs):
        if isinstance(message, dict):
            if "data" in message and "event" not in message:
                return

            if "event" in message:
                if message["event"] in self.events.relay_events:
                    await _run_handlers(
                        asyncio.create_task(
                            on_relay_handler(
                                self._instance_for(websocket), websocket, message
                            )
                        )
                        for on_relay_handler in self.events.relay_events[
                            message["event"]
                        ]
                    )

                    await self.sleep()

    async def ensure_instance(self, websocket: WebSocket, *args, **kwargs) -> Any:
        """Create (or reuse) the data object for this connection."""
        if self.share_instance:
            if self._shared_instance is None:
                if self.data_fetcher is None:
                    self._shared_instance = self.data_class(*args, **kwargs)
                else:
                    self._shared_instance = await self.data_fetcher.fetch(
                        self.data_class, *args, **kwargs
                    )
            return self._shared_instance
        key = id(websocket)
        if key not in self._instances:
            if self.data_fetcher is None:
                self._instances[key] = self.data_class(*args, **kwargs)
            else:
                self._instances[key] = await self.data_fetcher.fetch(
                    self.data_class, *args, **kwargs
                )
        return self._instances[key]

    def release_instance(self, websocket: WebSocket) -> None:
        if not self.share_instance:
            self._instances.pop(id(websocket), None)

    async def __call__(self, *args, **kwargs):
        # share_instance: ensure shared object exists.
        websocket = kwargs.get("websocket")
        if self.share_instance:
            await self.ensure_instance(
                websocket,
                *args,
                **{k: v for k, v in kwargs.items() if k != "websocket"},
            )
        elif websocket is not None:
            await self.ensure_instance(
                websocket,
                *args,
                **{k: v for k, v in kwargs.items() if k != "websocket"},
            )


class WebSocketClientHandler(object):
    def __init__(self, adapters: dict[str, GenericAdapter]):
        self.adapters: dict[str, GenericAdapter] = adapters
        self.all_connections: defaultdict = defaultdict(set)

    async def __call__(self, websocket: WebSocket, adapter_name: str, *args, **kwargs):
        adapter = self.adapters.get(adapter_name, None)
        message = None
        if adapter is None:
            await websocket.close()
            return
        else:
            if websocket not in adapter.connections:
                # await websocket.accept()
                adapter.connections.add(websocket)
                self.all_connections[adapter_name].add(websocket)

            try:
                # Per-connection (default) or shared data instance
                await adapter.ensure_instance(websocket, *args, **kwargs)  # type: ignore[attr-defined]
                await adapter.on_connect(websocket=websocket)
                while True:
                    message = await adapter.receive(websocket)
                    # disconnect frames may arrive as dict without text/bytes
                    if (
                        isinstance(message, dict)
                        and message.get("type") == "websocket.disconnect"
                    ):
                        break
                    on_receive_task = create_task(
                        adapter.on_receive(websocket=websocket, message=message)
                    )
                    on_relay_task = create_task(
                        adapter.on_relay(websocket=websocket, message=message)
                    )
                    await gather(on_receive_task, on_relay_task)
            except Exception as exc:
                # Keep teardown reliable; avoid silent infinite loops on protocol errors
                try:
                    await websocket.send_json(
                        {"event": "error", "data": {"type": type(exc).__name__}}
                    )
                except Exception:
                    pass
            finally:
                if websocket in adapter.connections:
                    adapter.connections.discard(websocket)
                    self.all_connections[adapter_name].discard(websocket)
                try:
                    await adapter.on_disconnect(
                        *args, websocket=websocket, message=message, **kwargs
                    )
                finally:
                    adapter.release_instance(websocket)  # type: ignore[attr-defined]


"""
usage 

app = Starlette()

class MyAdapter(WebSocketAdapter):
    ...

adapter = MyAdapter()
websocket_endpoint = WebSocketEndpoint(app, "/ws", adapter)

@app.websocket_route("/ws")
async def my_handler(websocket: WebSocket):
    await websocket_endpoint(websocket)
"""
