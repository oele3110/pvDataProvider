import asyncio

import websockets

connected_clients = set()
shutdown_event = asyncio.Event()  # event for shutdown
server_instance = None
send_task = None

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
                await asyncio.gather(*(client.send(data_to_send) for client in connected_clients), return_exceptions=True)
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
        if not shutdown_event.is_set():
            connected_clients.discard(websocket)
            print(f"❌ Client disconnected: {websocket.remote_address}")
            print(f"Connected clients: {len(connected_clients)}")


async def shutdown_websocket_server():
    global server_instance
    print(f"🔴 shutting down server ...")

    if connected_clients:
        print(f"📢 all clients informed about shutdown")
        try:
            tasks = [client.close(code=1001, reason="Server shutdown") for client in connected_clients]
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)  # wait a bit to ensure that all close frames are sent
        except Exception as e:
            print(f"⚠️ Error closing client: {e}")

    shutdown_event.set()

    if server_instance:
        server_instance.close()
        await server_instance.wait_closed()
        print("✅ WebSocket server closed")


async def start_websocket_server():
    global server_instance, send_task, shutdown_event
    server_instance = await websockets.serve(_handle_client, "0.0.0.0", 8765)
    send_task = asyncio.create_task(_send_data())
    await shutdown_event.wait()

    if send_task:
        send_task.cancel()
        try:
            await send_task
        except asyncio.CancelledError:
            print("📴 send_data task cancelled")
