from pydantic import BaseModel

class RoomCreateRequest(BaseModel):
    room_name: str
    owner_name: str

class UserCreateRequest(BaseModel):
    user_name: str
    room_code: str

class OwnerIdRequest(BaseModel):
    owner_id: int