import asyncio
import importlib.util

import aioconsole

from ..interface import BasicLogger, ILogger, IServer, ISupervisor
from ..model.event import (_EVENT_ARGS_CTX, _SERVER_CTX, EventArgs,
                           MCSR_AllLoaded, MCSR_AllStopped, MCSR_ExtsLoaded,
                           MCSR_Output, MCSR_Stderr, MCSR_Stdin, MCSR_Stdout,
                           ServerEventBus, ServerHandler, ServerHandlerMaker,
                           Singleton, SupervisorEvent, SupervisorEventBus,
                           SupervisorHandler, SupervisorHandlerMaker)
from ..typing import *
from ..utils.tools import PathUtils
from .server import Server, ServerLoader


class MCSupervisor(ISupervisor, Singleton):
    def __init__(self) -> None:
        self.servers: Dict[str, Server] = {}
        self.logger = BasicLogger('MCSR')

        self._aware_tasks: Dict[int, asyncio.Task] = {}
        self._server_buses: Dict[str, ServerEventBus] = {}
        self._server_handlers: List[ServerHandler] = []
        self._self_handlers: List[SupervisorHandler] = []
        self._self_handlerMaker = SupervisorHandlerMaker(self)
        self._self_bus = SupervisorEventBus(self)


    @property
    def server_ids(self) -> List[str]:
        return list(self.servers.keys())


    def add_server(self, id: str, java_path: str, server_jar_path: str, args: Union[str, List[str]]='', no_gui: bool=True, work_path: str=None, world_name: str='world', custom_logger: ILogger=None) -> None:
        self.servers[id] = Server(
            id=id, 
            server_loader=ServerLoader(java_path, server_jar_path, args, no_gui, work_path), 
            server_logger=custom_logger if custom_logger else BasicLogger(id), 
            world_name=world_name
        )
        self._server_buses[id] = self.servers[id]._event_bus


    def load_extension(self, ext_path: str) -> None:
        spec = importlib.util.spec_from_file_location(PathUtils.get_basename(ext_path), ext_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


    def server(self, id: str=None) -> ServerHandlerMaker:
        maker = ServerHandlerMaker(self, id)
        return maker


    def default_sever(self) -> ServerHandlerMaker:
        maker = ServerHandlerMaker(self, self.server_ids[0])
        return maker


    def register(self, event: Union[type, SupervisorEvent], aware: bool=False) -> Callable:
        return self._self_handlerMaker.register(event, aware)


    def on(self, event: Union[type, SupervisorEvent], func: Awaitable[None], aware: bool=False) -> None:
        if isinstance(event, type):
            event = event()
        handler = SupervisorHandler(event, func, aware)
        self._self_bus.register(handler)

    
    async def stdout(self, msg: str, custom_prefix: str=None) -> None:
        self.logger.log(msg, custom_prefix)
        await self._self_bus.emit(MCSR_Stdout, EventArgs(output=msg))
        await self._self_bus.emit(MCSR_Output, EventArgs(output=msg))


    async def stderr(self, msg: str, custom_prefix: str=None) -> None:
        self.logger.log(msg, custom_prefix)
        await self._self_bus.emit(MCSR_Stderr, EventArgs(output=msg))
        await self._self_bus.emit(MCSR_Output, EventArgs(output=msg))


    def broadcast(self, msg: str, exclude_self: bool=False) -> None:
        for server in self.servers.values():
            if server.id == _SERVER_CTX.id and exclude_self:
                continue
            server.send(msg)


    def get_server(self, id: str) -> IServer:
        return self.servers.get(id)


    def run(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run())


    async def _run(self) -> None:
        for handler in self._self_handlers:
            self._self_bus.register(handler)

        for handler in self._server_handlers:
            if handler.server_id is None:
                for server in self.servers.values():
                    server._event_bus.register(handler)
                continue
            server = self.servers.get(handler.server_id)
            if server is None:
                raise ValueError("不存在的服务器 id ")
            else:
                server._event_bus.register(handler)
        await self._self_bus.emit(MCSR_ExtsLoaded)

        for server in self.servers.values():
            asyncio.create_task(server._run())
        asyncio.create_task(self._forward_stdin())

        for server in self.servers.values():
            await server.loaded_flag.wait()
        await self._self_bus.emit(MCSR_AllLoaded)

        for server in self.servers.values():
            await server.stopped_flag.wait()
        await self._self_bus.emit(MCSR_AllStopped, force_wait=True)
        for task in self._aware_tasks.values():
            task.cancel()


    async def stop(self) -> None:
        tasks = []
        for server in self.servers.values():
            tasks.append(asyncio.create_task(server.stop()))
        await asyncio.wait(tasks)


    async def _forward_stdin(self) -> None:
        try:
            while True:
                line_with_eol = await aioconsole.ainput()
                line = line_with_eol.rstrip('\n')
                await self._self_bus.emit(MCSR_Stdin, EventArgs(output=line))
        except asyncio.CancelledError:
            pass

MCSR = MCSupervisor()
