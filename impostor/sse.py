from typing import Dict, Deque, Callable, Set
from collections import deque
from enum import Enum
from fastapi import Request;
import json

owner_messages: Dict[int, Deque[str]] = {}
player_messages: Dict[int, Deque[str]] = {}

class MessageType(Enum):
    JOINED = "joined"
    LEFT = "left"
    START = "start"
    END = "end"
    STOP = "stop"
    CLOSE = "close"

def get_joined_message(user_name: str) -> str:
    return json.dumps({"type": MessageType.JOINED.value, "user_name": user_name})

def get_left_message(user_name: str) -> str:
    return json.dumps({"type": MessageType.LEFT.value, "user_name": user_name})

def get_start_message(word) -> str:
    return json.dumps({"type": MessageType.START.value, "word":word})

def get_end_message() -> str:
    return json.dumps({"type": MessageType.END.value})

def get_stop_message(user_name: str) -> str:
    return json.dumps({"type": MessageType.STOP.value, "user_name": user_name})

def get_close_message(owner_name: str) -> str:
    return json.dumps({"type": MessageType.CLOSE.value, "owner_name": owner_name})

def register_owner(owner_id: int):
    if owner_id not in owner_messages:
        owner_messages[owner_id] = deque()

def register_player(player_id: int):
    if player_id not in player_messages:
        player_messages[player_id] = deque()

def unregister_owner(owner_id: int):
    if id in owner_messages:
        del owner_messages[id]

def unregister_player(player_id: int):
    if id in player_messages:
        del player_messages[id]

def _add_message(id: int, messages: Dict[int, Deque[str]], message: str):
    if id in messages:
        messages[id].append(message)

def add_owner_message(user_id: int, message: str):
    _add_message(user_id, owner_messages, message)

def add_player_message(player_id: int, message: str):
    _add_message(player_id, player_messages, message)

keep_alive: Set[int] = set()

def set_alive(room_id: int, alive: bool = True):
    if not alive:
        keep_alive.discard(room_id)
    else:
        keep_alive.add(room_id)
    
def is_alive(room_id: int):
    return room_id in keep_alive

def get_owner_message_generator(owner_id: int, room_id: int, request: Request, on_disconnect: Callable[[], None] = None):
    async def message_generator():
        import asyncio
        try:
            while is_alive(room_id) and not await request.is_disconnected():
                if owner_id in owner_messages and owner_messages[owner_id]:
                    yield owner_messages[owner_id].popleft()
                await asyncio.sleep(1) 
        except:
            print('exception disconnected')
        finally:
            print('owner disconnecting')
            if on_disconnect:
                on_disconnect()
    return message_generator 

def get_player_message_generator(user_id: int, room_id: int, on_disconnect: Callable[[], None] = None):
    async def message_generator():
        import asyncio
        try:
            while 1:
                if not is_alive(room_id):
                    if user_id in player_messages:
                        while player_messages[user_id]:
                            yield player_messages[user_id].popleft()
                    break
                if user_id in player_messages and player_messages[user_id]:
                    yield player_messages[user_id].popleft()
                await asyncio.sleep(1) 
        finally:
            print('player disconnecting')
            if on_disconnect:
                on_disconnect()
    return message_generator

# messages list
# player joined the room 'joined to owner
# player quit the room 'left' to owner
# game start 'start' to all
# game end 'end' to all
# room close 'close' to all