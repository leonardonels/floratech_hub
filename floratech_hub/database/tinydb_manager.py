from tinydb import TinyDB, Query

class DatabaseManager:
    def __init__(self, db_path="floratech_hub.json"):
        self.db = TinyDB(db_path)

    def save_message(self, message):
        self.db.insert({"message": message})

    def get_messages(self):
        return self.db.all()
