import asyncio
from datetime import datetime
import requests

import config
from lora.lora import LoRaModule
from database.database import DatabaseManager


def new_sensor(debug, db, lora, role = "sensor"):
    ack = 0
    id_max = db.get_max_sensor_id() +1

    while(ack != id_max):
        lora.send(id_max)
        message = lora.receive(60)
        
        '''it's possible to brick the sensor if the ack is sent, but not received'''
        if len(message) == 8:
            ack, ver = read_message(message)
            if ack != ver:
                print(f"Error: ack {ack} does not match sent id {ver}")
                return
            if debug:
                print(f'Ack message: {ack} {ver}')
        
        else:
            print('Timeout: No ack received within the specified time.')
            return

    if ack == id_max:   # need to check if the ack was successfully received
        db.save_sensor(id_max, role, str(datetime.now()), None)
        response = requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": id_max, "role": role, "last_ping": str(datetime.now()), "garden": None})
        if response.status_code == 200:
            print(role + ' saved!')

def add_garden(debug, db, id, role):
    response = requests.post(config.SERVER_URL + "add_garden/" + str(config.RASBERRY_ID), json = {"id": id, "role": role, "last_ping": str(datetime.now()), "garden": None})
    if response.status_code == 200:
        return response.json().get("garden")

    else:
        print(f"Error: {response.status_code}")
        return None

def add_moisture(debug, db, sensor_id, moisture, garden):
    '''moisture values check here'''
    db.save_moisture(str(datetime.now()), moisture, sensor_id, garden)
    if debug: print('moisture saved!')
    
    response = requests.post(config.SERVER_URL + "add_moisture/" + str(config.RASBERRY_ID), json = {'timestamp': str(datetime.now()), 'moisture': moisture, 'sensor_from': sensor_id, 'garden': garden})
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

async def sensor_warning_callback(db, id):
    while True:
        await asyncio.sleep(60)
        print("Starting sensor_warning_callback...")
        sensor = db.get_sensor(id)[0]
        if not sensor:
            return
        last_ping = datetime.strptime(sensor.get("last_ping"), "%Y-%m-%d %H:%M:%S.%f")
        if (datetime.now() - last_ping).seconds < 86400:
            print(f"Sensor {sensor.get('id')} started working, last ping: {last_ping}")
        requests.get(config.SERVER_URL + "sensor_working/" + str(config.RASBERRY_ID) + "/" + str(id))

async def h_callback(db):
    while True:
        await asyncio.sleep(3600)
        print("Starting h_callback...")
        sensors_json = db.get_sensors()
        for sensor in sensors_json:
            try:
                last_ping = datetime.strptime(sensor.get("last_ping"), "%Y-%m-%d %H:%M:%S.%f")
                if (datetime.now() - last_ping).seconds > 86400 and sensor.get("garden") != None:
                    print(f"Sensor {sensor.get('id')} stopped working, last ping: {last_ping}")
                    response = requests.get(config.SERVER_URL + "sensor_warning/" + config.RASBERRY_ID + "/" + str(sensor.get("id")) + "/sensor_timedout")
                    if response.status_code == 200:
                        sensor_warning_task = asyncio.create_task(sensor_warning_callback(db, sensor.get("id")))
            except Exception as e:
                print(f"Error processing sensor {sensor.get('id')}: {e}")
                pass

async def day_callback(db):
    while True:
        await asyncio.sleep(86400)  # 1 day delay
        print("Starting day_callback...")
        sensors_json = db.get_sensors()
        for sensor in sensors_json:
            last_ping = list(sensor.keys())[2]
            del sensor[last_ping]

        response = requests.post(config.SERVER_URL + "check_sensor/" + config.RASBERRY_ID, json = sensors_json)
        if response.status_code == 200:
            print("Server response received.")

            print(f"Local sensors: {sensors_json}")
            print(f"Server sensors: {response.json()}")
            if sensors_json != response.json():
                print("Sensors do not match!")
                for sensor in response.json():
                    if db.get_sensor(sensor.get("id"))[0]:
                        db.update_sensor(sensor.get("id"), sensor.get("role"), str(datetime.now()), sensor.get("garden"))
                '''for sensor in sensors_json:
                    if sensor not in response.json():
                        db.delete_sensor(sensor.get("id"))  TO DO'''
            else:   
                print("Sensors match!")

        else:
            print(f"Error: {response.status_code}")

def read_message(message):
    combined_hex = int.from_bytes(message, byteorder='big')
    for byte in message:
        print(f"Byte: {byte}")

    id = combined_hex >> 32
    moisture = combined_hex & 0xFFFFFFFF

    return id, moisture

async def main():
    lora = AsyncLoRaModule()
    db = DatabaseManager(db_path=config.DB_PATH)
    server = config.SERVER_URL
    debug = config.DEBUG

    # Start the timed callback task for periodic updates
    h_update_task = asyncio.create_task(h_callback(db))
    day_update_task = asyncio.create_task(day_callback(db))

    # Debug server management
    #if debug: db.save_sensor(10, "sensor", str(datetime.now()), None)
    #if debug: requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": 10, "role": "sensor", "last_ping": str(datetime.now()), "garden": None})
    #if debug: db.save_sensor(11, "sensor", str(datetime.now()), None)
    #if debug: requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": 11, "role": "sensor", "last_ping": str(datetime.now()), "garden": None})

    while True:
        try:
            message = await lora.async_receive()

            if message and len(message) == 8:  # Ensure the message length is exactly 8 characters
                sensor_id, moisture = read_message(message)
                if debug: print(f'message: {sensor_id} {moisture}')
                
                if sensor_id == 0 or sensor_id == 4294967295:  # if asking for sensor id == 0 -> sensor, else id = FFFF -> actuator
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
                        if debug: print(f'sensor {sensor_id} successfully updated!')

                        if role == "sensor":
                            add_moisture(debug, db, sensor_id, moisture, garden)
                        else:
                            '''h check'''
                            '''season check'''
                            '''ask django how much water for m**3 is needed for a certain garden'''
                            response = requests.post(config.SERVER_URL + "water/" + str(config.RASBERRY_ID), json = {"id": sensor_id}) #{"water": mm, "dim": m**3}
                            if response.status_code == 200:
                                '''answer time for pump ON'''
                                water_mm = response.json().get("water")
                                garden_area = response.json().get("dim")
                                lora.send(water_mm*garden_area/config.PUMP_RATE)
                            else:
                                print(f"Error: {response.status_code}")
        

        except asyncio.TimeoutError as e:
            print(f"Timeout occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")