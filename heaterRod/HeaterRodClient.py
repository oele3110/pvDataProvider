import asyncio

import aiohttp

from utils.Utils import process_sensor_value


class HeaterRodClient:
    def __init__(self, server, config, data_store):
        print("Initializing HeaterRodClient ...")
        self.server = server
        self._stop_event = asyncio.Event()
        self.config = config
        self.data_store = data_store

    async def start(self):
        print("Starting HeaterRodClient ...")
        async with aiohttp.ClientSession() as session:
            while not self._stop_event.is_set():
                data = await self.get_value(session, self.config)
                if data:
                    self.data_store.update(data)
                await asyncio.sleep(1)

    async def stop(self):
        print("Stopping HeaterRodClient ...")
        self._stop_event.set()

    async def get_value(self, session, config):
        try:
            async with session.get(f"http://{self.server}/data.jsn") as response:
                if response.status == 200:
                    received_data = await response.json()
                    return {key: process_sensor_value(received_data.get(key, None), config[key]) for key in config}
                else:
                    print(f"HTTP error: {response.status}")
                    return None
        except Exception as e:
            print(f"Error: {e}")
            return None
