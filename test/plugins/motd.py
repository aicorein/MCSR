from mcsr import MCSR, ServerOutput, eargs, server
from mcsr import JsonText, Colors, Texts
from datetime import datetime
from time import time
import json
import os


records = {
    'main': {},
    'mirrored': {},
    'creative': {}
}
plugin_dir = os.path.join(os.path.dirname(__file__), 'motd')
if not os.path.exists(plugin_dir):
    os.mkdir(plugin_dir)
play_datas_path = os.path.join(plugin_dir, '.play_datas')
if os.path.exists(play_datas_path):
    with open(play_datas_path, 'r') as fp:
        play_datas = json.load(fp)
else:
    play_datas = {}


def get_day() -> str:
    return datetime.fromtimestamp(time()).day


def get_play_days(username: str) -> int:
    global play_datas, play_datas_path
    matched = play_datas.get(username)
    if matched:
        if matched[0] != get_day():
            matched[0] = get_day()
            matched[1] += 1
    else:
        play_datas[username] = [get_day(), 1]
    
    with open(play_datas_path, 'w') as fp:
        json.dump(play_datas, fp, ensure_ascii=False, indent=2)
    return play_datas[username][1]


@MCSR.server("main").register(ServerOutput(r' (\S+) joined the game'))
async def main_motd():
    global records
    username = eargs.matched
    if records['main'].get(username) and get_day() == records['main'][username]:
        return
    text = Texts(
        JsonText('欢迎来到 HWS 服务器！今天是你游玩 HWS 的第 ', color=Colors.green),
        JsonText(f'{get_play_days(username)} ', color=Colors.gold),
        JsonText(f'天。\n', color=Colors.green),
        JsonText(f'你现在在 ', color=Colors.green),
        JsonText('main 子服', color=Colors.aqua),
        JsonText('。使用 /server 可切换子服。\n', color=Colors.green),
        JsonText('main 子服', color=Colors.aqua),
        JsonText('是 HWS 的核心，所有的生存活动将在这里展开，尽情探索叭~', color=Colors.green)
    ).format()
    server.send(f'/tellraw {username} {text}')
    records['main'][username] = get_day()


@MCSR.server("mirrored").register(ServerOutput(r' (\S+) joined the game'))
async def mirrored_motd():
    global records
    username = eargs.matched
    if records['mirrored'].get(username) and get_day() == records['mirrored'][username]:
        return
    text = Texts(
        JsonText('欢迎来到 HWS 服务器！今天是你游玩 HWS 的第 ', color=Colors.green),
        JsonText(f'{get_play_days(username)} ', color=Colors.gold),
        JsonText(f'天。\n', color=Colors.green),
        JsonText(f'你现在在 ', color=Colors.green),
        JsonText('mirrored 子服', color=Colors.aqua),
        JsonText('。使用 /server 可切换子服。\n', color=Colors.green),
        JsonText('mirrored 子服 ', color=Colors.aqua),
        JsonText('是 ', color=Colors.green),
        JsonText('main 子服', color=Colors.aqua),
        JsonText('的创造模式镜像，可以开展各种测试和调试~', color=Colors.green)
    ).format()
    server.send(f'/tellraw {username} {text}')
    records['mirrored'][username] = get_day()


@MCSR.server("creative").register(ServerOutput(r' (\S+) joined the game'))
async def creative_motd():
    global records
    username = eargs.matched
    if records['creative'].get(username) and get_day() == records['creative'][username]:
        return
    text = Texts(
        JsonText('欢迎来到 HWS 服务器！今天是你游玩 HWS 的第 ', color=Colors.green),
        JsonText(f'{get_play_days(username)} ', color=Colors.gold),
        JsonText(f'天。\n', color=Colors.green),
        JsonText(f'你现在在 ', color=Colors.green),
        JsonText('creative 子服', color=Colors.aqua),
        JsonText('。使用 /server 可切换子服。\n', color=Colors.green),
        JsonText('creative 子服', color=Colors.aqua),
        JsonText('是一个与其他子服无关的创造服，尽情玩耍吧~', color=Colors.green)
    ).format()
    server.send(f'/tellraw {username} {text}')
    records['creative'][username] = get_day()