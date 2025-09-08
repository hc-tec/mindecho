from fastapi import WebSocket
from typing import Dict, List, Set, DefaultDict
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.groups: DefaultDict[str, Set[str]] = defaultdict(set)  # group -> set(task_id)

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]
        # remove from all groups
        for group in list(self.groups.keys()):
            self.groups[group].discard(task_id)
            if not self.groups[group]:
                self.groups.pop(group, None)

    async def send_json(self, task_id: str, data: dict):
        if task_id in self.active_connections:
            await self.active_connections[task_id].send_json(data)

    def join_group(self, task_id: str, group: str):
        self.groups[group].add(task_id)

    def leave_group(self, task_id: str, group: str):
        if group in self.groups:
            self.groups[group].discard(task_id)
            if not self.groups[group]:
                self.groups.pop(group, None)

    async def broadcast_json(self, group: str, data: dict):
        for task_id in list(self.groups.get(group, set())):
            ws = self.active_connections.get(task_id)
            if ws is None:
                self.groups[group].discard(task_id)
                continue
            try:
                await ws.send_json(data)
            except Exception:
                # drop broken connection
                self.disconnect(task_id)

manager = ConnectionManager()
