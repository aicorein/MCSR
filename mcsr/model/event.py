import asyncio
import re
from abc import ABC, abstractmethod
from asyncio import Future
from contextvars import ContextVar, Token

from ..interface import IServer, ISupervisor
from ..typing import *


class Singleton:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '__instance__'):
            cls.__instance__ = super(Singleton, cls).__new__(cls)
        return cls.__instance__


class EventArgs:
    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def add(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def remove(self, *args) -> None:
        for k in args:
            self.__dict__.pop(k)


_EVENT_ARGS_VAR = ContextVar("_EVENT_ARGS_VAR")
_SERVER_VAR = ContextVar("_SERVER_VAR")


class EventArgsLocal(Singleton):
    def __init__(self) -> None:
        object.__setattr__(self, '__storage__', _EVENT_ARGS_VAR)
        self.__storage__: ContextVar[Event]

    def __setattr__(self, __name: str, __value: Any) -> None:
        setattr(self.__storage__.get(), __name, __value)

    def __getattr__(self, __name: str) -> Any:
        return getattr(self.__storage__.get(), __name)
    
    def _add_ctx(self, ctx: "Event") -> Token:
        return self.__storage__.set(ctx)
    
    def _del_ctx(self, token: Token) -> None:
        self.__storage__.reset(token)
_EVENT_ARGS_CTX = EventArgsLocal()
_EVENT_ARGS_CTX: EventArgs


class ServerVarLocal(Singleton):
    __slots__ = tuple(
        list(
            filter(lambda x: not (len(x) >= 2 and x[:2] == '__'), dir(IServer))
        )
        + ['__storage__']
        + list(IServer().__dict__.keys())
    )

    def __init__(self) -> None:
        object.__setattr__(self, '__storage__', _SERVER_VAR)
        self.__storage__: ContextVar[Event]

    def __setattr__(self, __name: str, __value: Any) -> None:
        setattr(self.__storage__.get(), __name, __value)

    def __getattr__(self, __name: str) -> Any:
        return getattr(self.__storage__.get(), __name)
    
    def _add_ctx(self, ctx: "Event") -> Token:
        return self.__storage__.set(ctx)
    
    def _del_ctx(self, token: Token) -> None:
        self.__storage__.reset(token)
_SERVER_CTX = ServerVarLocal()
_SERVER_CTX: IServer


class Handler(ABC):
    def __init__(self, event: "Event", method: Awaitable[None]) -> None:
        super().__init__()
        self._method = method
        self.event = event

    @abstractmethod
    async def handle(self, *args) -> None:
        pass


class ServerHandler(Handler):
    def __init__(self, server_id: Optional[str], event: "ServerEvent", method: Awaitable[None], aware: bool=False) -> None:
        super().__init__(event, method)
        self.event: ServerEvent
        self.server_id = server_id
        self._aware = aware

    async def handle(self, server: IServer, args: EventArgs=None) -> None:
        try:
            args_token = _EVENT_ARGS_CTX._add_ctx(args)
            server_token = _SERVER_CTX._add_ctx(server)
            t = asyncio.create_task(self._method())
            if self._aware:
                server._aware_tasks[id(t)] = t
            await t
        finally:
            server._aware_tasks.pop(id(t), None)
            _SERVER_CTX._del_ctx(server_token)
            _EVENT_ARGS_CTX._del_ctx(args_token)


class SupervisorHandler(Handler):
    def __init__(self, event: "SupervisorEvent", method: Awaitable[None], aware: bool=False) -> None:
        super().__init__(event, method)
        self.event: SupervisorEvent
        self._aware = aware

    async def handle(self, supervisor: ISupervisor, args: EventArgs=None) -> None:
        try:
            args_token = _EVENT_ARGS_CTX._add_ctx(args)
            t = asyncio.create_task(self._method())
            if self._aware:
                supervisor._aware_tasks[id(t)] = t
            await t
        finally:
            supervisor._aware_tasks.pop(id(t), None)
            _EVENT_ARGS_CTX._del_ctx(args_token)


class ServerHandlerMaker:
    def __init__(self, supervisor_ref: ISupervisor, server_id: str=None) -> None:
        self.server_id = server_id
        self.supervisor_ref = supervisor_ref
    
    def register(self, event: Union[type, "ServerEvent"], aware: bool=False) -> Callable:
        if isinstance(event, type):
            event = event()
        def func(cb: Callable) -> None:
            handler = ServerHandler(self.server_id, event, cb, aware)
            self.supervisor_ref._server_handlers.append(handler)
        return func


class SupervisorHandlerMaker:
    def __init__(self, supervisor_ref: ISupervisor) -> None:
        self.supervisor_ref = supervisor_ref
    
    def register(self, event: Union[type, "SupervisorEvent"], aware: bool=False) -> Callable:
        if isinstance(event, type):
            event = event()
        def func(cb: Callable) -> None:
            handler = SupervisorHandler(event, cb, aware)
            self.supervisor_ref._self_handlers.append(handler)
        return func


class Event(ABC):
    def __init__(self) -> None:
        super().__init__()

    @property
    def type(self) -> str:
        return self.__class__.__name__
    
    @abstractmethod
    def make_coroutine(self, handler: Handler, args: EventArgs=None) -> Coroutine:
        return handler.handle(args)


######################################################


class ServerEvent(Event):
    def __init__(self) -> None:
        super().__init__()

    def make_coroutine(self, server: IServer, handler: ServerHandler, args: EventArgs=None) -> Coroutine:
        return handler.handle(server, args)


class ServerBeforeStart(ServerEvent):
    def __init__(self) -> None:
        super().__init__()


class ServerLoaded(ServerEvent):
    def __init__(self) -> None:
        super().__init__()


class ServerOutput(ServerEvent):
    def __init__(self, match: re.Pattern=None) -> None:
        super().__init__()
        self.pattern = match

    def make_coroutine(self, server: IServer, handler: ServerHandler, args: EventArgs = None) -> Coroutine:
        async def func():
            if self.pattern is None:
                await handler.handle(server, args)
            else:
                matched = re.findall(self.pattern, args.output)
                if len(matched):
                    args.add(matched=matched[0])
                    await handler.handle(server, args)
        return func()


class ServerBeforeStop(ServerEvent):
    def __init__(self) -> None:
        super().__init__()


class ServerStopped(ServerEvent):
    def __init__(self) -> None:
        super().__init__()


######################################################


class SupervisorEvent(Event):
    def __init__(self) -> None:
        super().__init__()

    def make_coroutine(self, supervisor: ISupervisor, handler: SupervisorHandler, args: EventArgs=None) -> Coroutine:
        return handler.handle(supervisor, args)


class MCSR_Stdin(SupervisorEvent):
    def __init__(self) -> None:
        super().__init__()


class MCSR_ExtsLoaded(SupervisorEvent):
    def __init__(self) -> None:
        super().__init__()


class MCSR_AllLoaded(SupervisorEvent):
    def __init__(self) -> None:
        super().__init__()


class MCSR_Stdout(SupervisorEvent):
    def __init__(self, match: re.Pattern=None) -> None:
        super().__init__()
        self.pattern = match

    def make_coroutine(self, supervisor: ISupervisor, handler: SupervisorHandler, args: EventArgs=None) -> Coroutine:
        async def func():
            if self.pattern is None:
                await handler.handle(supervisor, args)
            else:
                matched = re.findall(self.pattern, args.output)
                if len(matched):
                    args.add(matched=matched[0])
                    await handler.handle(supervisor, args)
        return func()


class MCSR_Stderr(SupervisorEvent):
    def __init__(self, match: re.Pattern=None) -> None:
        super().__init__()
        self.pattern = match

    def make_coroutine(self, supervisor: ISupervisor, handler: SupervisorHandler, args: EventArgs=None) -> Coroutine:
        async def func():
            if self.pattern is None:
                await handler.handle(supervisor, args)
            else:
                matched = re.findall(self.pattern, args.output)
                if len(matched):
                    args.add(matched=matched[0])
                    await handler.handle(supervisor, args)
        return func()


class MCSR_Output(SupervisorEvent):
    def __init__(self, match: re.Pattern=None) -> None:
        super().__init__()
        self.pattern = match

    def make_coroutine(self, supervisor: ISupervisor, handler: SupervisorHandler, args: EventArgs=None) -> Coroutine:
        async def func():
            if self.pattern is None:
                await handler.handle(supervisor, args)
            else:
                matched = re.findall(self.pattern, args.output)
                if len(matched):
                    args.add(matched=matched[0])
                    await handler.handle(supervisor, args)
        return func()


class MCSR_AllStopped(SupervisorEvent):
    def __init__(self) -> None:
        super().__init__()


######################################################


class EventBus(ABC):
    def __init__(self) -> None:
        super().__init__()
        self.handler_map: Dict[str, List[Handler]] = {}
        self.fut_map: Dict[str, List[Future]] = {}
        
        self._lock = asyncio.Lock()

    @abstractmethod
    def register_fut(self, event_class: Type[Event]) -> Future:
        if self.fut_map.get(event_class.__name__) is None:
            self.fut_map[event_class.__name__] = []
        fut = Future()
        self.fut_map[event_class.__name__].append(fut)
        return fut

    @abstractmethod
    def register(self, handler: Handler) -> None:
        event = handler.event
        if self.handler_map.get(event.type) is None:
            self.handler_map[event.type] = []
        self.handler_map[event.type].append(handler)

    @abstractmethod
    async def emit(self, event_type: Type[Event], args: EventArgs=None) -> None:
        pass


class ServerEventBus(EventBus):
    def __init__(self, server_ref: IServer) -> None:
        super().__init__()
        self.handler_map: Dict[str, List[ServerHandler]]
        self.server_ref = server_ref

    def register_fut(self, event_class: Type[ServerEvent]) -> Future:
        super().register_fut(event_class)

    def register(self, handler: ServerHandler) -> None:
        super().register(handler)

    async def emit(self, event_class: Type[ServerEvent], args: EventArgs=None, force_wait: bool=False) -> None:
        if args is None:
            args = EventArgs()

        handlers = self.handler_map.get(event_class.__name__)
        if handlers is None:
            return
        else:
            tasks = []
            for handler in handlers:
                event = handler.event
                t = asyncio.create_task(event.make_coroutine(self.server_ref, handler, args))
                tasks.append(t)
            if force_wait:
                await asyncio.wait(tasks)

        async with self._lock:
            futs = self.fut_map.get(event_class.__name__)
            if futs is None:
                return
            else:
                for fut in futs:
                    fut.set_result(True)
                self.fut_map[event_class.__name__].clear()


class SupervisorEventBus(EventBus):
    def __init__(self, supervisor_ref: ISupervisor) -> None:
        super().__init__()
        self.handler_map: Dict[str, List[SupervisorHandler]]
        self.supervisor_ref = supervisor_ref

    def register_fut(self, event_class: Type[SupervisorEvent]) -> Future:
        super().register_fut(event_class)

    def register(self, handler: SupervisorHandler) -> None:
        super().register(handler)

    async def emit(self, event_class: Type[SupervisorEvent], args: EventArgs=None, force_wait: bool=False) -> None:
        if args is None:
            args = EventArgs()
        
        handlers = self.handler_map.get(event_class.__name__)
        if handlers is None:
            return
        else:
            tasks = []
            for handler in handlers:
                event = handler.event
                t = asyncio.create_task(event.make_coroutine(self.supervisor_ref, handler, args))
                tasks.append(t)
            if force_wait:
                await asyncio.wait(tasks)

        async with self._lock:
            futs = self.fut_map.get(event_class.__name__)
            if futs is None:
                return
            else:
                for fut in futs:
                    fut.set_result(True)
                self.fut_map[event_class.__name__].clear()
