import asyncio
from datetime import datetime

import config
from lora.lora import LoRaModule
from database.database import DatabaseManager

def read_message(message):
    combined_hex = int.from_bytes(message, byteorder='big')

    id = combined_hex >> 32
    moisture = combined_hex & 0xFFFFFFFF

    return id, moisture

class AsyncLoRaModule:
    def __init__(self):
        self.lora = LoRaModule(frequency=config.LORA_FREQUENCY)

    async def async_receive(self, timeout=5):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.receive, timeout)

    def receive(self, timeout):
        try:
            message = self.lora.receive(timeout=timeout)
            if message is None:
                raise asyncio.TimeoutError("No message received within the specified timeout")
            return message
        except Exception as e:
            print(f"Error in receive: {e}")
            return None
        
    def send(self, message):
        self.lora.send_id(message)
        try:
            if message is None:
                raise asyncio.TimeoutError("No message received within the specified timeout")
        except Exception as e:
            print(f"Error encurred while answering: {e}")
            return None

async def timed_callback(server, db):
    while True:
        await asyncio.sleep(3600)  # 1 hour delay
        #messages = db.get_messages_to_send()  # Assume this method fetches messages to send
        #for message in messages:
        #    server.send_data({"message": message})

async def main():
    lora = AsyncLoRaModule()
    db = DatabaseManager(db_path=config.DB_PATH)
    #server = ServerAPI(config.SERVER_URL)

    # Start the timed callback task for periodic updates
    #update_task = asyncio.create_task(timed_callback(server, db))

    while True:
        try:
            message = await lora.async_receive()
            message = [0,0,0,0,0,0,0,0] #debug

            if message and len(message) == 8:  # Ensure the message length is exactly 8 characters
                sensor_id, moisture = read_message(message)
                print(sensor_id, moisture)
                if sensor_id == 0:  # if asking for sensor id == 0 -> sensor, else id = FFFF -> actuator
                    id_max = db.get_max_sensor_id()
                    lora.send(id_max+1)
                    db.save_sensor(id_max+1, "sensor", str(datetime.now()), 0)

                else:
                    _, role, last_ping, garden = db.get_sensor(sensor_id)
                    if role != None and last_ping != None and garden != None:

                        if role == "sensor":
                            # save the moisture on django
                            db.save_moisture(str(datetime.now()), moisture, sensor_id, garden)
                            # update the sensor configuration on the db
                            db.update_sensor(sensor_id, role, str(datetime.now()), garden)
                            #check on last ping
                            #if (datetime.now() - last_ping).seconds > 3600:
                                # send a message to the sensor to check on it
                                #pass 

                        elif role == "actuator":
                            # answer
                            pass
        
        except asyncio.TimeoutError as e:
            print(f"Timeout occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())