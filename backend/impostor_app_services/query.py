from typing import Optional, Sequence


from sqlalchemy.orm import Session
from sqlalchemy import select, delete, and_, func

from impostor_app_services import db

def room_get(room_id: int, ses: Session) -> Optional[db.Room]:
    query = select(db.Room).where(db.Room.id == room_id)
    return ses.execute(query).scalars().first()

def room_exists(room_id: int, ses: Session) -> bool:
    return room_get(room_id, ses) is not None

def room_get_by_code(room_code: str, ses: Session) -> Optional[db.Room]:
    query = select(db.Room).where(db.Room.code == room_code)
    return ses.execute(query).scalars().first()

def room_get_by_owner(owner_id: int, ses: Session) -> Optional[db.Room]:
    query = select(db.Room).where(db.Room.owner_id == owner_id)
    return ses.execute(query).scalars().first()

def room_exists_by_code(room_code: str, ses: Session) -> bool:
    return room_get_by_code(room_code, ses) is not None

def room_is_available(room_id: int, ses: Session) -> bool:
    return room_get(room_id, ses).available

def room_set_available(room_id: int, available: bool, ses: Session):
    room = room_get(room_id, ses)
    if room:
        room.available = available
        ses.commit()
    else:
        raise ValueError(f"Room with id {room_id} does not exist.")

def room_is_owner(room_id: int, user_id: int, ses: Session) -> bool:
    query = select(db.Room).where(and_(db.Room.id == room_id, db.Room.owner_id == user_id))
    return ses.execute(query).first() is not None

def room_get_players(room_id: int, ses: Session) -> Sequence[db.User]:
    query = select(db.User) \
        .where(db.User.room_id == room_id) \
        .where(db.Room.id == room_id) \
        .where(db.User.id != db.Room.owner_id)
    return ses.execute(query).scalars().fetchall()

def room_all(ses: Session):
    query = select(db.Room)
    return ses.execute(query).scalars().all()

def room_delete(room_id: int, ses: Session):
    query = delete(db.User).where(db.User.room_id == room_id)
    ses.execute(query)
    query = delete(db.Room).where(db.Room.id == room_id)
    ses.execute(query)

def user_get(user_id: int, ses: Session):
    query = select(db.User).where(db.User.id == user_id)
    return ses.execute(query).scalars().first()

def user_any_alias_in_room(room_id: int, user_name: str, ses: Session) -> bool:
    query = select(db.User).where(and_(db.User.room_id == room_id, db.User.name == user_name))
    return ses.execute(query).first() is not None

def user_count_in_room(room_id: int, ses: Session):
    return ses.query(db.User).filter(db.User.room_id == room_id).count()

def user_get_by_room(room_id: int, ses: Session):
    query = select(db.User).where(db.User.room_id == room_id)
    return ses.execute(query).scalars().fetchall()

def user_exists(user_id: int, ses: Session) -> bool:
    return user_get(user_id, ses) is not None

def user_all(ses: Session):
    query = select(db.User)
    return ses.execute(query).scalars().all()

def user_delete(user_id: int, ses: Session):
    query = delete(db.User).where(db.User.id == user_id)
    ses.execute(query)