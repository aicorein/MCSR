from mcsr import MCSR
from mcsr import PathUtils


java_path='/home/melodyecho/servers/dragonwell-17.0.2.0.2+8-GA/bin/java'
args='-Xms8192M -Xmx20480M -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=40 -XX:G1MaxNewSizePercent=50 -XX:G1HeapRegionSize=16M -XX:G1ReservePercent=15 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=20 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true'
world_name='HelloWorld'


def get_server_jar(id: str) -> str:
    return f'/home/melodyecho/servers/mc_server/{id}/start.jar'

def get_ext_path(filename: str) -> str:
    return PathUtils.join(PathUtils.get_dir(__file__), 'plugins', filename)


MCSR.add_server(id='main', java_path=java_path, server_jar_path=get_server_jar('main'), args=args, world_name=world_name)
MCSR.add_server(id='creative', java_path=java_path, server_jar_path=get_server_jar('creative'), args=args, world_name=world_name)
MCSR.add_server(id='mirrored', java_path=java_path, server_jar_path=get_server_jar('mirrored'), args=args, world_name=world_name)
MCSR.load_extension(get_ext_path('console.py'))
MCSR.load_extension(get_ext_path('autosave.py'))
MCSR.load_extension(get_ext_path('msg_bridge.py'))
MCSR.load_extension(get_ext_path('motd.py'))
MCSR.run()
