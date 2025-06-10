import requests
import random

from fastapi import FastAPI, APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from impostor.request import *
from impostor import db, query, sse
from impostor.roomcode import generate_code

api_version = 'v1'
router = APIRouter(prefix=f'/impostor/{api_version}')

@router.post("/room")
async def room(req: RoomCreateRequest):
    with Session(db.engine) as session:
        owner = db.User(name=req.owner_name, room_id=None)
        session.add(owner)
        session.commit()
        while 1:
            room_code = generate_code()
            if not query.room_exists_by_code(room_code, session):
                break
        room = db.Room(owner_id=owner.id, code=room_code)
        session.add(room)
        session.commit()
        owner.room_id = room.id
        room_id = room.id
        owner_id = owner.id
        session.commit()
        sse.set_alive(room_id, True)
    return {'room_id': room_id, 'room_code': room_code, 'owner_id': owner_id}

@router.get('/room')
async def room_all():
    with Session(db.engine) as session:
        return {'rooms':query.room_all(session)}

def clean_room(room_id: int):
    with Session(db.engine) as session:
        room = query.room_get(room_id, session)
        owner = query.user_get(room.owner_id, session)
        sse.unregister_owner(owner.id)
        for p in query.room_get_players(room.id, session) :
            sse.add_player_message(p.id, sse.get_close_message(owner.name))
        sse.set_alive(room.id, False)
        # sse.unregister_owner(owner_id)
        query.room_delete(room.id, session)
        session.commit()

@router.get('/sse/owner/{owner_id}')
async def owner_sse(owner_id: int):
    with Session(db.engine) as session:
        if not query.user_exists(owner_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {owner_id} does not exist')
        if not query.room_is_owner(query.user_get(owner_id, session).room_id, owner_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'user is not an owner of any room')
        room_id = query.user_get(owner_id, session).room_id
    
    sse.register_owner(owner_id)
    generator = sse.get_owner_message_generator(owner_id, room_id, lambda: clean_room(room_id) if sse.is_alive(room_id) else None)
    return EventSourceResponse(generator(), media_type='text/event-stream')

@router.post('/user')
async def user(req: UserCreateRequest):
    with Session(db.engine) as session:

        if not query.room_exists_by_code(req.room_code, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'room {req.room_code} does not exist')
        
        room_id = query.room_get_by_code(req.room_code, session).id
        
        if query.user_any_alias_in_room(room_id, req.user_name, session):
            raise HTTPException(status.HTTP_409_CONFLICT, f'user named {req.user_name} already joined this room')
        
        user = db.User(name=req.user_name, room_id=room_id)
        session.add(user)
        session.commit()
        user_id=user.id

    def on_disconnect():
        if sse.is_alive(room_id): #disconnected unexpectedly
            with Session(db.engine) as session:
                sse.unregister_player(user_id)
                room = query.room_get(room_id, session)
                user = query.user_get(user_id, session)
                sse.add_owner_message(room.owner_id, sse.get_left_message(user.name))
                query.user_delete(user_id, session)
                session.commit()
            
    sse.register_player(user_id)
    generator = sse.get_player_message_generator(user_id, room_id, on_disconnect)
    sse.add_owner_message(query.room_get(room_id, session).owner_id, sse.get_joined_message(user.name))
    return EventSourceResponse(generator(), media_type='text/event-stream')

@router.get('/user')
async def user_all():
    with Session(db.engine) as session:
        return {'users':query.user_all(session)}

@router.post('/start')
async def start(req: OwnerIdRequest):
    with Session(db.engine) as session:
        if not query.user_exists(req.owner_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {req.owner_id} does not exist')
        
        user = query.user_get(req.owner_id, session)
        if not query.room_is_owner(user.room_id, req.owner_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'only room owner can start the game')
        
        if query.user_count_in_room(user.room_id, session) < 3:
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'not enough players to start the game')
        
        session.commit()

        room_id = user.room_id

        word = requests.get('https://random-word-api.vercel.app/api?words=1').json()[0]

        #implement random impostor assignment

        players = query.room_get_players(room_id, session)
        players_list = list(players)
        players_list.append(user)  # add owner to the list

        impostor_index = random.randint(0, len(players_list) - 1)

        for i, p in enumerate(players_list):
            if i == impostor_index:
                if p.id == user.id:
                    sse.add_owner_message(user.id, sse.get_start_message('IMPOSTOR'))
                else:
                    sse.add_player_message(p.id, sse.get_start_message('IMPOSTOR'))
            else:
                if p.id == user.id:
                    sse.add_owner_message(user.id, sse.get_start_message(word))
                else:
                    sse.add_player_message(p.id, sse.get_start_message(word))

    
    return {"message": "Game started"}

@router.post('/close')
async def close(req: OwnerIdRequest):
    sse.set_alive(room_id, False)
    with Session(db.engine) as session:
        if not query.user_exists(req.owner_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {req.owner_id} does not exist')
        
        owner = query.user_get(req.owner_id, session)
        if not query.room_is_owner(owner.room_id, owner.id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'only room owner can close the room')
        session.commit()
        room_id = owner.room_id

    
    return {"message": "Room closed"}

app = FastAPI()
app.include_router(router)