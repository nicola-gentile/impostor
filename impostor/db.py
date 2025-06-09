from sqlalchemy import Integer, String, ForeignKey, Boolean, create_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'user'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String, nullable=False)
    room_id = mapped_column(ForeignKey('room.id'))

class Room(Base):
    __tablename__ = 'room'

    id = mapped_column(Integer, primary_key=True)
    code = mapped_column(String(8), nullable=False, unique=True, index=True)
    owner_id = mapped_column(ForeignKey('user.id'), nullable=False)

metadata = Base.metadata
engine = create_engine('sqlite:///:memory:')

metadata.create_all(engine)




