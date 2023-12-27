import asyncio
import re
import subprocess
from asyncio import Future, Lock, Queue, StreamReader, StreamWriter, Task
from asyncio.subprocess import Process

from ..interface import ILogger, IServer, IServerLoader
from ..model.event import (EventArgs, ServerBeforeStart, ServerBeforeStop,
                           ServerEvent, ServerEventBus, ServerHandler,
                           ServerLoaded, ServerOutput, ServerStopped)
from ..typing import *
from ..utils.tools import PathUtils


class ServerLoader(IServerLoader):
    def __init__(self, java_path: str, server_jar_path: str, args: Union[str, List[str]]='', no_gui: bool=True, work_path: str=None) -> None:
        self.java_path = java_path
        self.args = args
        self.nogui = no_gui

        self.server_jar_path = server_jar_path
        if not PathUtils.isabs(self.server_jar_path):
            raise ValueError("服务端 jar 路径必须为绝对路径")
        self.work_path = work_path if work_path else PathUtils.get_dir(self.server_jar_path)

        args_str = ' '.join(self.args) if isinstance(self.args, list) else self.args
        self.cmd = f"{self.java_path} {args_str} -jar {self.server_jar_path} {'nogui' if no_gui else ''}"
        self.split_cmd = self.cmd.split(' ')

    async def load(self) -> Process:
        return await asyncio.create_subprocess_exec(*self.split_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                                    stderr=subprocess.PIPE, cwd=self.work_path)


class Server(IServer):
    def __init__(self, id: str, server_loader: ServerLoader, server_logger: ILogger, world_name: str='world') -> None:
        self.id = id
        self.proc: Process = None
        self.stdin: StreamWriter = None
        self.stdout: StreamReader = None
        self.stderr: StreamReader = None
        self.logger = server_logger
        
        self._loader = server_loader
        self._lock = Lock()
        self._buf: Queue[str] = Queue()
        self._passed_buf: Queue[str] = Queue()
        self._core_tasks: Tuple[Task, ...] = None
        self._aware_tasks: Dict[int, Task] = {}
        self._event_bus = ServerEventBus(self)

        self.running_flag = asyncio.Event()
        self.loaded_flag = asyncio.Event()
        self.stopped_flag = asyncio.Event()
        self.stopped_flag.set()

        self.cwd = server_loader.work_path
        self.world_folder_name = world_name
        
        if not PathUtils.isabs(self.cwd):
            raise ValueError("服务端工作路径必须为绝对路径")


    # TODO: 未来合并两个设计
    async def _stdout_watcher(self) -> None:
        try:
            while True:
                output = (await self.stdout.readline()).decode().rstrip('\n')
                if not output:
                    await asyncio.sleep(0.1)
                    continue

                if not self.loaded_flag.is_set() and len(re.findall('Done.', output)):
                    self.loaded_flag.set()
                    await self._event_bus.emit(ServerLoaded)

                await self._buf.put(output)

                if self._lock.locked():
                    continue
                async with self._lock:
                    while not self._buf.empty():
                        output = await self._buf.get()
                        await self._event_bus.emit(ServerOutput, EventArgs(output=output))
        except asyncio.CancelledError:
            pass


    async def _stderr_watcher(self) -> None:
        try:
            while True:
                output = (await self.stderr.readline()).decode().rstrip('\n')
                if not output:
                    await asyncio.sleep(0.1)
                    continue

                if not self.loaded_flag.is_set() and len(re.findall('Done.', output)):
                    self.loaded_flag.set()
                    await self._event_bus.emit(ServerLoaded)
                
                await self._buf.put(output)

                if self._lock.locked():
                    continue
                async with self._lock:
                    while not self._buf.empty():
                        output = await self._buf.get()
                        await self._event_bus.emit(ServerOutput, EventArgs(output=output))
        except asyncio.CancelledError:
            pass


    def on(self, event: Union[type, ServerEvent], func: Awaitable[None], aware: bool=False) -> None:
        if isinstance(event, type):
            event = event()
        handler = ServerHandler(self.id, event, func, aware)
        self._event_bus.register(handler)


    def at(self, event_class: Type[ServerEvent]) -> Future:
        return self._event_bus.register_fut(event_class)


    def send(self, content: str) -> None:
        self.stdin.write(f'{content}\n'.encode())


    async def interact(self, sent_str: str, expect_pattern: str, timeout: float=None, match_reuse: bool=False, block_pattern: str=None) -> Union[Tuple[str, ...], None]:
        async def find():
            output = None
            loop_flag = True
            while loop_flag:
                while not self._passed_buf.empty():
                    output = await self._passed_buf.get()
                    await self._event_bus.emit(ServerOutput, EventArgs(output=output))
                
                output = await self._buf.get()
                match = re.findall(expect_pattern, output)
                if len(match):
                    loop_flag = False
                    if match_reuse:
                        await self._passed_buf.put(output)
                    return match[0]
                else:
                    if block_pattern and len(re.findall(block_pattern, output)):
                        continue
                    await self._passed_buf.put(output)
        
        async with self._lock:
            self.stdin.write(f'{sent_str}\n'.encode())
            match_res = None
            try:
                match_res = await asyncio.wait_for(find(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
            finally:
                return match_res


    def aware_task(self, coro: Coroutine, *, name: Optional[str]=None) -> Task:
        t = asyncio.create_task(coro, name=name)
        self._aware_tasks[id(t)] = t
        return t


    async def _run(self) -> None:
        await self._event_bus.emit(ServerBeforeStart, force_wait=True)
        self.proc = await self._loader.load()
        self.stdin = self.proc.stdin
        self.stdout = self.proc.stdout
        self.stderr = self.proc.stderr
        self._core_tasks = tuple(map(asyncio.create_task, (
            self._stdout_watcher(),
            self._stderr_watcher(),
        )))
        self.running_flag.set()
        self.stopped_flag.clear()

        await self.proc.wait()
        for task in self._core_tasks:
            if not task.done():
                task.cancel()
        # 确保非正常结束都有 loaded flag
        self.loaded_flag.set()
        self.running_flag.clear()
        self.stopped_flag.set()
        await self._event_bus.emit(ServerStopped)
        for task in self._aware_tasks.values():
            task.cancel()


    async def stop(self) -> None:
        await self._event_bus.emit(ServerBeforeStop, force_wait=True)
        self.send('/stop')
        await self.stopped_flag.wait()


    async def force_stop(self) -> None:
        self.proc.terminate()
        await self.stopped_flag.wait()
