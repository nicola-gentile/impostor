import requests
import random

from fastapi import FastAPI, APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from impostor_app_services.request import *
from impostor_app_services import db, query, sse
from impostor_app_services.roomcode import generate_code

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
        room = db.Room(name=req.room_name, owner_id=owner.id, code=room_code, available=True)
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

def clean_room(owner_id: int):
    with Session(db.engine) as session:
        room = query.room_get_by_owner(owner_id, session)
        owner = query.user_get(owner_id, session)
        sse.unregister_owner(owner_id)
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
    
    sse.register_owner(owner_id)
    generator = sse.get_owner_message_generator(owner_id, lambda: clean_room(owner_id))
    return EventSourceResponse(generator(), media_type='text/event-stream')

@router.get('/sse/player/{user_id}')
async def room_sse(user_id: int):
    with Session(db.engine) as session:
        if not query.user_exists(user_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {user_id} does not exist')
        room_id = query.user_get(user_id, session).room_id
        if not query.room_exists(room_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'room {room_id} does not exist')
    def on_disconnect():
        if sse.is_alive(room_id): #disconnected unexpectedly
            with Session(db.engine) as session:
                sse.unregister_player(user_id)
                room = query.room_get(room_id, session)
                user = query.user_get(user_id, session)
                if not query.room_is_available(room_id, session): #disconnected during game
                    sse.add_owner_message(room.owner_id, sse.get_stop_message(user.name))
                    for player in query.room_get_players(room_id, session):
                        sse.add_player_message(player.id, sse.get_stop_message(user.name))
                    query.room_set_available(room_id, True, session)
                else:
                    sse.add_owner_message(room.owner_id, sse.get_left_message(user.name))
                query.user_delete(user_id, session)
                session.commit()
            

    sse.register_player(user_id)
    generator = sse.get_player_message_generator(user_id, room_id, on_disconnect)
    return EventSourceResponse(generator(), media_type='text/event-stream')

@router.post('/user')
async def user(req: UserCreateRequest):
    with Session(db.engine) as session:

        if not query.room_exists_by_code(req.room_code, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'room {req.room_code} does not exist')
        
        room_id = query.room_get_by_code(req.room_code, session).id
        if not query.room_is_available(room_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'joining the room is forbidden while playing')
        
        if query.user_any_alias_in_room(room_id, req.user_name, session):
            raise HTTPException(status.HTTP_409_CONFLICT, f'user named {req.user_name} already joined this room')
        
        user = db.User(name=req.user_name, room_id=room_id)
        session.add(user)
        session.commit()
        user_id=user.id
    sse.add_owner_message(query.room_get(room_id, session).owner_id, sse.get_joined_message(user.name))
    return { 'user_id': user_id }

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
        
        if not query.room_is_available(user.room_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'game already started')
        
        if query.user_count_in_room(user.room_id, session) < 3:
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'not enough players to start the game')
        
        query.room_set_available(user.room_id, False, session)
        session.commit()

        room_id = user.room_id

        word = requests.get('https://random-word-api.herokuapp.com/word?number=1').json()[0]

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

@router.post('/end')
async def end(req: OwnerIdRequest):
    with Session(db.engine) as session:
        if not query.user_exists(req.owner_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {req.owner_id} does not exist')
        
        user = query.user_get(req.owner_id, session)
        if not query.room_is_owner(user.room_id, req.owner_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'only room owner can end the game')
        
        if query.room_is_available(user.room_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'game is not started yet')
        
        query.room_set_available(user.room_id, True, session)
        session.commit()

        room_id = user.room_id

    for p in query.room_get_players(room_id, session):
        sse.add_player_message(p.id, sse.get_end_message())
    
    return {"message": "Game ended"}

@router.post('/close')
async def close(req: OwnerIdRequest):
    with Session(db.engine) as session:
        if not query.user_exists(req.owner_id, session):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f'user with id {req.owner_id} does not exist')
        
        user = query.user_get(req.owner_id, session)
        user_name = user.name
        if not query.room_is_owner(user.room_id, req.owner_id, session):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'only room owner can end the game')
        session.commit()

        room_id = user.room_id

    for p in query.room_get_players(room_id, session):
        sse.add_player_message(p.id, sse.get_close_message(user_name))

    clean_room(req.owner_id)
    
    return {"message": "Room closed"}

app = FastAPI()
app.include_router(router)