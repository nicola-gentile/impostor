import db
from roomcode import generate_code
from sqlalchemy.orm import Session

with Session(db.engine) as session:
    code = generate_code()
    user = db.User(name='nick', room_id=None)
    session.add(user)
    session.commit()
    room1 = db.Room(name='room1', owner_id=user.id, code=code)
    room2 = db.Room(name='room2', owner_id=user.id, code=code)
    user.room_id=room1.id
    session.add(room1)
    session.add(room2)
    session.commit()
    print(repr(db.metadata.tables))