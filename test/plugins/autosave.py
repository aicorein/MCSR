import asyncio
import os
import datetime
from mcsr import MCSR, ServerLoaded, eargs, server


bak_nums = 5
interval_time = 20*60


@MCSR.server().register(ServerLoaded)
async def backup_main():
    global interval_time
    while True:
        await backup()
        await asyncio.sleep(interval_time)


def get_time_str():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


def fresh_day_bak(backup_path: str):
    folder = os.path.join(server.cwd, 'day_backup')
    if not os.path.exists(folder):
        os.mkdir(folder)
    
    today_bak_path = os.path.join(folder, datetime.datetime.now().strftime("%Y-%m-%d"))
    if os.path.exists(today_bak_path):
        os.system(f'rm -rf {today_bak_path} --no-preserve-root')
    os.system(f'cp -r {backup_path} {today_bak_path}')


async def backup():
    global bak_nums
    # log_func = partial(MCSR.logger.log, custom_prefix=f"autosave {server.id}")

    matched = await server.interact('/list', r'There are (\d+) of a max of (\d+) players online')
    player_num, max_num = map(int, matched)
    if player_num == 0:
        with open(os.path.join(server.cwd, 'auto-save.log'), 'a') as fp:
            print(get_time_str(), '无玩家，本次自动保存任务取消', flush=True, file=fp)
        return
    
    backup_folder = os.path.join(server.cwd, 'backup')
    if not os.path.exists(backup_folder):
        os.mkdir(backup_folder)
    
    server.send('/tellraw @a [{"text": "[Server] 服务器自动保存中...（你可以继续游戏）", "color": "gold"}]')
    await server.interact('/save-off', r'Automatic saving is now disabled')
    await server.interact('/save-all flush', r'Saved the game', block_pattern=r'(Saving the game)|(ThreadedAnvilChunkStorage)')

    save_name = get_time_str()+'_bak'
    save_path = os.path.join(backup_folder, save_name)
    world_path = os.path.join(server.cwd, server.world_folder_name)
    os.system(f'cp -r {world_path} {save_path}')
    await server.interact('/save-on', r'Automatic saving is now enabled')
    # log_func()
    server.send('/tellraw @a [{"text": "[Server] 服务器自动保存完成", "color": "gold"}]')
    fresh_day_bak(save_path)
    with open(os.path.join(server.cwd, 'auto-save.log'), 'a') as fp:
        print(get_time_str(), f'成功完成自动保存，保存为：{save_name}', flush=True, file=fp)


    bak_paths = [os.path.join(backup_folder, dir) for dir in os.listdir(backup_folder)]
    bak_paths = sorted(bak_paths, key=lambda x: os.path.getmtime(x))
    for bak_path in bak_paths[:-bak_nums]:
        os.system(f'rm -rf {bak_path} --no-preserve-root')