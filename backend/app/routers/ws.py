from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.notifications.websocket import manager

router = APIRouter()


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time trade execution notifications.
    Clients connect here to receive live updates during order execution.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; receive pings or commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
