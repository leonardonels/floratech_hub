import asyncio
from datetime import datetime
import requests

import config
from lora.lora import LoRaModule
from database.database import DatabaseManager


def read_message(message):
    combined_hex = int.from_bytes(message, byteorder='big')

    id = combined_hex >> 32
    moisture = combined_hex & 0xFFFFFFFF

    return id, moisture

def new_sensor(debug, db, lora, role = "sensor"):
    ack = 0
    id_max = db.get_max_sensor_id() +1

    while(ack != id_max):
        lora.send(id_max)
        message = lora.receive(60)
        
        '''it's possible to brick the sensor if the ack is sent, but not received'''
        if len(message) == 8:
            ack, _ = read_message(message)
            if debug:
                print(f'message: {ack} {_}')
        
        else:
            print('Timeout: No ack received within the specified time.')
            break

    if ack == id_max:   # need to check if the ack was successfully received
        db.save_sensor(id_max, role, str(datetime.now()), None)
        response = requests.post(config.SERVER_URL + "new_sensor/" + config.RASBERRY_ID, json = {"id": id_max, "role": role, "last_ping": str(datetime.now()), "garden": None})
        if response.status_code == 200:
            print(role + ' saved!')

def add_garden(debug, db, id, role):
    response = requests.post(config.SERVER_URL + "add_garden/" + config.RASBERRY_ID, json = {"id": id, "role": role, "last_ping": str(datetime.now()), "garden": None})
    if response.status_code == 200:
        return response.json().get("garden")

    else:
        print(f"Error: {response.status_code}")
        return None

def add_moisture(debug, db, sensor_id, moisture, garden):
    '''moisture values check here'''
    db.save_moisture(str(datetime.now()), moisture, sensor_id, garden)
    if debug: print('moisture saved!')
    
    response = requests.post(config.SERVER_URL + "add_moisture/" + config.RASBERRY_ID, json = {'timestamp': str(datetime.now()), 'moisture': moisture, 'sensor_from': sensor_id, 'garden': garden})
    if response.status_code == 200:
        print('moisture sent!')  


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

async def warning_callback(server, db, id):
    while True:
        await asyncio.sleep(30)
        time = datetime.now()
        sensor = db.get_sensor(id)
        _, _, last_ping, _ = sensor.get("id"), sensor.get("role"), sensor.get("last_ping"), sensor.get("garden")
        if (datetime.now() - last_ping).seconds < 86400:
            requests.get(config.SERVER_URL + "sensor_warking/" + config.RASBERRY_ID + "/" + id)

async def h_callback(server, db):
    while True:
        await asyncio.sleep(3600)   # 1 hour delay
        sensors_json = db.get_sensors()
        time = datetime.now()
        for sensor in sensors_json:
            id, _, last_ping, _ = sensor.get("id"), sensor.get("role"), sensor.get("last_ping"), sensor.get("garden")
            if (datetime.now() - last_ping).seconds > 86400:
                requests.get(config.SERVER_URL + "sensor_warning/" + config.RASBERRY_ID + "/" + id + "/last_ping_too_old")
                warking_update_task = asyncio.create_task(warning_callback(server, db, id))            

async def day_callback(server, db):
    while True:
        await asyncio.sleep(86400)  # 1 day delay
        sensors_json = db.get_sensors()
        sensor_response = requests.post(config.SERVER_URL + "check_sensor", json = sensors_json)
        if sensors_json != sensor_response:
            '''fai cose'''
            pass


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

            if message and len(message) == 8:  # Ensure the message length is exactly 8 characters
                sensor_id, moisture = read_message(message)
                if debug: print(f'message: {sensor_id} {moisture}')
                
                if sensor_id == 0 or sensor_id == 65535:  # if asking for sensor id == 0 -> sensor, else id = FFFF -> actuator
                    if debug: print('setup sensor!')
                    
                    new_sensor(debug, db, lora, "sensor" if sensor_id == 0 else "actuator")

                else:   # sensor/actuator already configured
                    sensor = db.get_sensor(sensor_id)
                    if sensor:
                        _, role, _, garden = sensor[0].values()
                    else:
                        role, garden = None, None
                    
                    if garden == None:
                        garden = add_garden(debug, db, sensor_id, role)
                    
                    if garden != None:
                        db.update_sensor(sensor_id, role, str(datetime.now()), garden)
                        if debug: print(f'garden {garden} successfully updated!')

                        if role == "sensor":
                            add_moisture(debug, db, sensor_id, moisture, garden)
                        else:
                            pass
        

        except asyncio.TimeoutError as e:
            print(f"Timeout occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())