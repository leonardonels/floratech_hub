import asyncio
from floratech_hub.lora.lora import LoRaModule
from floratech_hub.database.tinydb_manager import DatabaseManager
from floratech_hub.server.server_api import ServerAPI
from datetime import datetime

def read_message(message):
    combined_hex = int.from_bytes(message, byteorder='big')

    id = combined_hex >> 32
    moisture = combined_hex & 0xFFFFFFFF

    return id, moisture

class AsyncLoRaModule:
    def __init__(self):
        self.lora = LoRaModule()

    async def receive(self):
        while True:
            message = await self.lora.receive()
            if message:
                return message

async def timed_callback(server, db):
    while True:
        await asyncio.sleep(3600)  # 1 hour delay
        messages = db.get_messages_to_send()  # Assume this method fetches messages to send
        for message in messages:
            server.send_data({"message": message})

async def main():
    lora = AsyncLoRaModule()
    db = DatabaseManager()
    #server = ServerAPI(config.SERVER_URL)

    # Start the timed callback task for periodic updates
    #update_task = asyncio.create_task(timed_callback(server, db))

    while True:
        message = await lora.receive()

        if message and len(message) == 8:  # Ensure the message length is exactly 8 characters
            sensor_id, moisture = read_message(message)
            if sensor_id == 0:  # if asking for sensor id == 0 -> sensor, else id = FFFF -> actuator
                id_max = db.get_max_sensor_id()
                lora.send(id_max+1)
                db.save_sensor(id_max+1, "sensor", datetime.now(), 0)
                print("sensor added")
            
            else:
                _, role, last_ping, garden = db.get_sensor(sensor_id)

                if role == "sensor":
                    # save the moisture on django
                    db.save_moisture(datetime.now(), moisture, sensor_id, garden)
                    # update the sensor configuration on the db
                    db.update_sensor(sensor_id, role, datetime.now(), garden)
                    #check on last ping
                    if (datetime.now() - last_ping).seconds > 3600:
                        # send a message to the sensor to check on it
                        pass 

                elif role == "actuator":
                    # answer
                    pass

        # End this loop iteration by creating a new task waiting for another message
        lora_task = asyncio.create_task(lora.receive())

if __name__ == "__main__":
    asyncio.run(main())