# About MCSR
MCSR is a project named "Minecraft Server Refabricated" based on Python and asyncio. Now is still under developing.

This project plan to build a wrapped minecraft server by manage the server console IO asynchronously. After that it'll provides event mechanism to help developers develop plugins to handle the server events.

# What it can do
- build a bot in your server
- events synchronization among servers
- some automation task
- ...

# Support Plan
These servers are on the future support list:
- Vanilla
- Fabric
- Forge
- Neo Forge
- ...

# Attention
**MCSR core can't process private message events(send and receive), because private messages are invisible to server console. But it can be implemented in plugins.** To achieve handle private message events must preprocessing server network traffic. Also, preprocessing needs to build a server proxy. But with different server types, the communication protocols are usually different. So we can't write universial codes of this part in core module, but we'll place APIs to support its implementation.
