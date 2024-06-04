from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
import string
import random

app = FastAPI()

# Define the origins that should be allowed to make requests to the API
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8001",
    "*"
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms = {}

class CreateRoomRequest(BaseModel):
    room_name: str
    user_name: str
    num_players: conint(ge=1, le=4)

class JoinRoomRequest(BaseModel):
    room_code: str
    user_name: str

def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.post("/create_room")
async def create_room(request: CreateRoomRequest):
    room_code = generate_room_code()
    while room_code in rooms:
        room_code = generate_room_code()
    
    rooms[room_code] = {
        "name": request.room_name,
        "host": request.user_name,
        "num_players": request.num_players,
        "clients": {request.user_name: None}  # Initialize with host's name but no WebSocket yet
    }
    return {"room_code": room_code}

@app.post("/join_room")
async def join_room(request: JoinRoomRequest):
    room_code = request.room_code
    user_name = request.user_name
    
    if room_code in rooms and len(rooms[room_code]["clients"]) < rooms[room_code]["num_players"]:
        rooms[room_code]["clients"][user_name] = None  # Add user to the room with no WebSocket yet
        return {"message": f"{user_name} joined room {room_code}"}
    else:
        raise HTTPException(status_code=404, detail="Room not found or full")

@app.websocket("/ws/{room_code}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_name: str):
    await websocket.accept()
    if room_code in rooms and user_name in rooms[room_code]["clients"]:
        rooms[room_code]["clients"][user_name] = websocket
        try:
            while True:
                data = await websocket.receive_text()
                for client_name, client_ws in rooms[room_code]["clients"].items():
                    if client_ws and client_ws != websocket:
                        await client_ws.send_text(data)
        except WebSocketDisconnect:
            rooms[room_code]["clients"][user_name] = None
            if not any(rooms[room_code]["clients"].values()):
                del rooms[room_code]
    else:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
