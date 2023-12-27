import asyncio
import datetime
from abc import ABC, abstractmethod
from asyncio import Future, Task
from asyncio.subprocess import Process

from .typing import *


class ISupervisor(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._server_handlers: list
        self._self_handlers: list
        self._aware_tasks: Dict[int, Task]


class IServerLoader(ABC):
    def __init__(self) -> None:
        self.java_path: str = None
        self.args: str = None
        self.server_jar_path: str = None
        self.nogui: bool = None
        self.work_path: str = None
        self.cmd: str = None

    @abstractmethod
    def load(self) -> Process:
        pass


class ILogger(ABC):
    @abstractmethod
    def log(self, msg: str) -> None:
        pass


class BasicLogger(ILogger):
    def __init__(self, default_prefix: str) -> None:
        self.prefix = default_prefix

    def log(self, msg: str, custom_prefix: str=None) -> None:
        if len(msg) <= 2000:
            if not custom_prefix:
                print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}]', f"[{self.prefix}] " + msg)
            else:
                print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}]', f"[{custom_prefix}] " + msg)
        else:
            if not custom_prefix:
                print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}]', f"[{self.prefix}] " + msg[:2000] + f' ...（已省略 {len(msg)-2000} 个字符）')
            else:
                print(f'[{datetime.datetime.now().strftime("%H:%M:%S")}]', f"[{custom_prefix}] " + msg[:2000] + f' ...（已省略 {len(msg)-2000} 个字符）')




class IServer:
    def __init__(self) -> None:
        self.id: str = None
        self.logger: ILogger = None
        self.running_flag: asyncio.Event() = None
        self.loaded_flag: asyncio.Event() = None
        self.stopped_flag: asyncio.Event() = None
        self.cwd: str = None
        self.world_folder_name: str = None

    @abstractmethod
    def on(self, event: type, func: Awaitable[None], aware: bool=False) -> None:
        pass

    @abstractmethod
    def at(self, event_class: type) -> Future:
        pass

    @abstractmethod
    def send(self, content: str) -> None:
        pass

    @abstractmethod
    async def interact(self, sent_str: str, expect_pattern: str, timeout: float=5, match_reuse: bool=False, block_pattern: str=None) -> Union[Tuple[str, ...], None]:
        pass

    @abstractmethod
    def aware_task(self, coro: Coroutine, *, name: Optional[str]=None) -> asyncio.Task:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def force_stop(self) -> None:
        pass