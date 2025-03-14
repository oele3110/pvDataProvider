import asyncio

import aiohttp


class HeaterRod:
    def __init__(self, server, values, data_store):
        print("Init HeaterRod ...")
        self.server = server
        self._stop_event = asyncio.Event()
        self.values = values
        self.data_store = data_store

    async def start(self):
        print("Starting HeaterRod ...")
        async with aiohttp.ClientSession() as session:
            while not self._stop_event.is_set():
                data = await self.get_value(session, self.values)
                if data:
                    self.data_store.update(data)
                await asyncio.sleep(1)

    async def stop(self):
        print("Stopping HeaterRod ...")
        self._stop_event.set()

    async def get_value(self, session, values):
        try:
            async with session.get(f"http://{self.server}/data.jsn") as response:
                if response.status == 200:
                    received_data = await response.json()
                    return {key: received_data.get(key, None) for key in values}
                else:
                    print(f"HTTP error: {response.status}")
                    return None
        except Exception as e:
            print(f"Error: {e}")
            return None
