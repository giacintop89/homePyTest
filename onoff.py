import asyncio
import os

from tapo import ApiClient


async def main() -> None:
    username = os.environ["TAPO_USERNAME"]  # your Tapo account email
    password = os.environ["TAPO_PASSWORD"]
    ip = os.environ["TAPO_IP"]              # the plug's local IP, e.g. 192.168.1.50

    client = ApiClient(username, password)

    device = await client.p100(ip)  # P100 plug
    await device.on()
    await asyncio.sleep(1)
    await device.off()
    await asyncio.sleep(1)
    await device.on()
    await asyncio.sleep(1)
    await device.off()
if __name__ == "__main__":
    asyncio.run(main())
