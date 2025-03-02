from floratech_hub.lora.lora import LoRaModule
from floratech_hub.database.tinydb_manager import DatabaseManager
from floratech_hub.server.server_api import ServerAPI
import config

def main():
    lora = LoRaModule()
    db = DatabaseManager()
    server = ServerAPI(config.SERVER_URL)

    while True:
        message = lora.receive()
        if message:
            print(f"Messaggio ricevuto: {message}")
            db.save_message(message)
            server.send_data({"message": message})

if __name__ == "__main__":
    main()
