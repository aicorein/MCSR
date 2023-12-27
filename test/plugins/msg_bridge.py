from mcsr import eargs, server, MCSR, ServerLoaded, ServerOutput, MCSR_AllLoaded
from mcsr import JsonText, Texts, Colors


@MCSR.register(MCSR_AllLoaded)
async def greeting():
    MCSR.logger.log("消息 bridge 已启动")


@MCSR.server().register(ServerLoaded)
async def bridge():
    server.on(ServerOutput(r' ([a-zA-Z0-9]+) » (.*)'), forward)


async def forward():
    username, msg = eargs.matched
    text = Texts(
        JsonText('[', color=Colors.dark_gray),
        JsonText(f'{server.id} 子服', color=Colors.white),
        JsonText('] ', color=Colors.dark_gray),
        JsonText(f'{username}', color=Colors.white),
        JsonText(' » ', color=Colors.dark_gray),
        JsonText(f'{msg}', color=Colors.white)
    ).format()
    MCSR.broadcast(f'/tellraw @a {text}', exclude_self=True)


