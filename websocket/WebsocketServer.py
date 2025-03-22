import asyncio
import websockets

connected_clients = set()
shutdown_event = asyncio.Event()  # event for shutdown

data_to_send = None


def update_data(data):
    global data_to_send
    data_to_send = data


async def _send_data():
    # stop sending data if shutdown event is set
    while not shutdown_event.is_set():
        # only send data if there are connected clients
        if connected_clients:
            try:
                await asyncio.gather(*(client.send(data_to_send) for client in connected_clients))
            except websockets.exceptions.ConnectionClosedOK:
                print("Client already disconnected, sending data not possible")
        await asyncio.sleep(1)


async def _handle_client(websocket):
    connected_clients.add(websocket)
    print(f"✅ Client connected: {websocket.remote_address}")
    print(f"Connected clients: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            print(f"❌ Client disconnected: {websocket.remote_address}")
            print(f"Connected clients: {len(connected_clients)}")


async def shutdown():
    print(f"🔴 shutting down server ...")

    if connected_clients:
        print(f"📢 all clients informed about shutdown")
        tasks = [client.close(code=1001, reason="Server shutdown") for client in connected_clients]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)  # wait a bit to ensure that all close frames are sent

    shutdown_event.set()


async def start_websocket_server():
    # start websocket server and stop it if shutdown event is set
    stop = asyncio.Future()  # future to stop server

    async with websockets.serve(_handle_client, "0.0.0.0", 8765):
        print("🚀 websocket server running of port 8765...")
        await asyncio.gather(_send_data(), stop)  # run server until stop signal
