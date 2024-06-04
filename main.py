from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict

app = FastAPI()

rooms: Dict[str, Dict[WebSocket, str]] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    room_id = None
    player_symbol = None
    await websocket.accept()

    # Join or create a room
    if 'room_id' in websocket.query_params:
        room_id = websocket.query_params['room_id']
        if room_id not in rooms:
            await websocket.close(code=1008, reason="Room not found")
            return
        else:
            if len(rooms[room_id]) == 2:
                await websocket.close(code=1008, reason="Room is full")
                return
            player_symbol = 'O' if len(rooms[room_id]) == 0 else 'X'
            rooms[room_id][websocket] = player_symbol
    else:
        room_id = str(len(rooms) + 1)
        rooms[room_id] = {websocket: 'X'}
        player_symbol = 'X'
        await websocket.send_json({'type': 'room_created', 'room_id': room_id})

    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'move':
                for client, symbol in rooms[room_id].items():
                    if client != websocket:
                        await client.send_json({'type': 'move', 'cell_index': data['cell_index'], 'value': player_symbol})

    except WebSocketDisconnect:
        rooms[room_id].pop(websocket)
        if not rooms[room_id]:
            rooms.pop(room_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)