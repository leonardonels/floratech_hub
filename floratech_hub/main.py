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
        self.lora = LoRaModule()

    async def async_receive(self, timeout=5):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.receive, timeout)

    def receive(self, timeout=5):
        try:
            message = self.lora.receive_bytes(timeout=timeout)
            if message is None:
                raise asyncio.TimeoutError("No message received within the specified timeout")
            return message
        except Exception as e:
            print(f"Error in receive: {e}")
            return None
        
    def send(self, message):
        self.lora.send_id(message)




# call warning
# mandare elenco all sensor con tutto
# check con mappa completa
#
# push unused sensors or actuators from db
# get sensor and actuators configuration
# save newly configured sensors or actuators
# 
# push moistures
# get actuators policy


async def h_callback(server, db):
    while True:
        await asyncio.sleep(3600)   # 1 hour delay
        sensors_json = db.get_sensors()
        time = datetime.now()
        for sensor in sensors_json:
            _, _, last_ping, _ = sensor.get("id"), sensor.get("role"), sensor.get("last_ping"), sensor.get("garden")
            if (datetime.now() - last_ping).seconds > 86400:
                '''send waring to django'''

async def day_callback(server, db):
    while True:
        await asyncio.sleep(86400)  # 1 day delay
        sensors_json = db.get_sensors()
        '''push actual sensor/actuators configuration asking its correctness'''




async def main():
    lora = AsyncLoRaModule()
    db = DatabaseManager(db_path=config.DB_PATH)
    server = config.SERVER_URL
    debug = config.DEBUG

    # Start the timed callback task for periodic updates
    h_update_task = asyncio.create_task(h_callback(server, db))
    day_update_task = asyncio.create_task(day_callback(server, db))

    while True:
        try:
            message = await lora.async_receive()
            if debug:
                if len(message)!=8:
                    print(message)
                else:
                    print('message received!')

            if message and len(message) == 8:  # Ensure the message length is exactly 8 characters
                sensor_id, moisture = read_message(message)
                if debug:
                    print(f'message: {sensor_id} {moisture}')
                
                if sensor_id == 0 or sensor_id == 65535:  # if asking for sensor id == 0 -> sensor, else id = FFFF -> actuator
                    ack = sensor_id
                    id_max = db.get_max_sensor_id() +1
                    
                    while(ack != id_max):
                        lora.send(id_max)
                        message = lora.receive(60)
                        
                        if len(message) == 8:
                            ack, _ = read_message(message)
                            if debug:
                                print(f'message: {ack} {_}')
                        
                        else:
                            if debug:
                                print('Timeout: No ack received within the specified time.')
                            break
                    
                    if ack == id_max:   # need to check if the ack was successfully received
                        if sensor_id == 0:
                            db.save_sensor(id_max, "sensor", str(datetime.now()), 0)
                        else:
                            db.save_sensor(id_max, "actuator", str(datetime.now()), 0)

                        sensor_json = db.get_sensor(id_max)
                        '''send new json to django to add the sensor'''

                        if debug:
                            print('saved!')

                else:   # sensor/actuator already configured
                    result = db.get_sensor(sensor_id)
                    if result:
                        sensor_data = result[0]
                        _, role, last_ping, garden = sensor_data.get("id"), sensor_data.get("role"), sensor_data.get("last_ping"), sensor_data.get("garden")
                    else:
                        role, last_ping, garden = None, None, None  # Default values
                    
                    _, role, last_ping, garden = result[0].values()
                    if garden == 0:
                        '''ask django if sensor number sensor_id has been assigend to a garden'''

                    if role != None and last_ping != None and garden != None and garden != 0:
                    
                        if role == "sensor":
                            db.save_moisture(str(datetime.now()), moisture, sensor_id, garden)
                            db.update_sensor(sensor_id, role, str(datetime.now()), garden)

                        elif role == "actuator":
                            # answer
                            pass
        
        except asyncio.TimeoutError as e:
            print(f"Timeout occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())