from mcsr import (MCSR, CmdParser, MCSR_AllLoaded, MCSR_AllStopped,
                  MCSR_ExtsLoaded, MCSR_Stdin, ServerBeforeStart, ServerLoaded,
                  ServerOutput, ServerStopped, eargs, server)

cur_server = next(iter(MCSR.servers.values()))
active_flags = {id: True for id in MCSR.server_ids}
parser = CmdParser('.', ' ')


@MCSR.server().register(ServerBeforeStart)
async def detect():
    async def handle_error():
        MCSR.logger.log(f'服务端 {server.id} 启动失败，即将强行关闭')
        await server.force_stop()
    server.on(ServerOutput('Failed to start the minecraft server'), handle_error)


@MCSR.server().register(ServerLoaded)
async def afterloaded():
    server.logger.log(f"服务端 {server.id} 已完成加载")
    async def OutputManager():
        if active_flags[server.id] and 'No player was found' not in eargs.output:
            server.logger.log(eargs.output)
    server.on(ServerOutput, OutputManager)


@MCSR.server().register(ServerStopped)
async def afterClose():
    server.logger.log(f"服务端 {server.id} 已关闭")


@MCSR.register(MCSR_ExtsLoaded)
async def printInfo():
    logo = """
ooo        ooooo   .oooooo.    .oooooo..o ooooooooo.   
`88.       .888'  d8P'  `Y8b  d8P'    `Y8 `888   `Y88. 
 888b     d'888  888          Y88bo.       888   .d88' 
 8 Y88. .P  888  888           `"Y8888o.   888ooo88P'  
 8  `888'   888  888               `"Y88b  888`88b.    
 8    Y     888  `88b    ooo  oo     .d8P  888  `88b.  
o8o        o888o  `Y8bood8P'  8""88888P'  o888o  o888o 
"""
    logo_strs = logo.split('\n')
    for s in logo_strs:
        MCSR.logger.log(s)
    MCSR.logger.log("MC Supervisor Refabricated（MCSR）版本：v1.0.0，开发者：aicorein")
    MCSR.logger.log(f"已注册的 MCSR 事件处理器数：{len(MCSR._self_handlers)}")
    MCSR.logger.log(f"已注册的服务端事件处理器数：{len(MCSR._server_handlers)}")
    MCSR.logger.log(f"运行服务端个数：{len(MCSR.servers)}")
    MCSR.logger.log("开始启动已添加的服务端")


@MCSR.register(MCSR_AllStopped)
async def afterAllstopped():
    MCSR.logger.log('所有服务端已关闭，MCSR 将停止运行')


@MCSR.register(MCSR_AllLoaded)
async def afterAllLoaded():
    global cur_server
    MCSR.logger.log('所有服务端已经加载完成')
    MCSR.logger.log(f'stdin 当前默认指向服务端 {cur_server.id}')


@MCSR.register(MCSR_Stdin)
async def InputManager():
    global cur_server, active_flags
    output = eargs.output
    
    matched = parser.parse(output)
    if cur_server._lock.locked():
        MCSR.logger.log('当前有任务正在等待输出，请等待其完成后再与服务端交互')
        return
    if matched is None:
        cur_server.send(output)
        return
    elif matched.verify('io-change', 1):
        await stdin_change(matched)
    elif matched.verify('io-stat'):
        await stat()
    elif matched.verify('io-toggle', 1):
        await stdout_toggle(matched)
    elif matched.verify('stop'):
        await stop_all()
    else:
        MCSR.logger.log('未知命令或命令参数缺失，请检查输入')


async def stdin_change(matched):
    global cur_server
    id = matched.args[0]
    if id in MCSR.server_ids:
        cur_server = MCSR.servers[id]
        MCSR.logger.log(f'stdin 已切换至服务端 {id}')
    else:
        MCSR.logger.log('不存在的服务器 id')


async def stat():
    global cur_server
    MCSR.logger.log(f'stdin 当前指向服务端 {cur_server.id}')
    MCSR.logger.log(f'各服务端 stdout 开关状态：')
    for id in MCSR.server_ids:
        MCSR.logger.log(f"服务端 {id}: {'on' if active_flags[id] else 'off'}")


async def stop_all():
    global active_flags
    MCSR.logger.log(f'正在停止所有服务端...')
    for k in active_flags.keys():
        active_flags[k] = False
    await MCSR.stop()


async def stdout_toggle(matched):
    global active_flags
    id = matched.args[0]
    if id in MCSR.server_ids:
        active_flags[id] = not active_flags[id]
        MCSR.logger.log(f"服务端 {id} stdout 状态已切换为: {'on' if active_flags[id] else 'off'}")
    else:
        MCSR.logger.log('不存在的服务器 id')
