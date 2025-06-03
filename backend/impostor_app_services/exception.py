
class RoomClosedError(Exception):
    """Exception raised when trying to perform an action on a closed room."""
    def __init__(self, message="The room is closed.", session=None):
        self.message = message
        self.session = session
        super().__init__(self.message)