from datetime import datetime, timedelta
import requests
import asyncio

from config import OPTIMAL_START_HOUR, OPTIMAL_END_HOUR
from database.database import DatabaseManager
from lora.lora import LoRaModule
import config


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

def try_later(debug, lora, message = -30):
    if debug: print("Retrying later...")
    lora.send(message)

# Not great, but works, for now
def get_season():
    """Returns 'spring', 'summer', 'autumn', or 'winter' based on the date."""
    month = datetime.now().month
    day = datetime.now().day

    if (month == 12 and day >= 21) or (1 <= month <= 2) or (month == 3 and day < 20):
        return 'winter'
    elif (month == 3 and day >= 20) or (4 <= month <= 5) or (month == 6 and day < 21):
        return 'spring'
    elif (month == 6 and day >= 21) or (7 <= month <= 8) or (month == 9 and day < 22):
        return 'summer'
    else:
        return 'autumn'

def is_optimal_time(now, season):
    """Checks if the current hour is within the optimal window."""
    return OPTIMAL_START_HOUR <= now.hour < OPTIMAL_END_HOUR

def calculate_sleep_until_optimal(now):
    """Returns NEGATIVE seconds to sleep until the next optimal window."""
    next_start = now.replace(hour=OPTIMAL_START_HOUR, minute=0, second=0, microsecond=0)
    if now.hour >= OPTIMAL_END_HOUR:
        next_start = next_start.replace(day=now.day + 1)
    elif now.hour < OPTIMAL_START_HOUR:
        pass
    return -int((next_start - now).total_seconds())  # make it negative

def is_temperature_ok(temperature):
    if temperature < 5 or temperature > 35:
        return False
    return True

def adjust_pump_time_by_temperature(pump_time, temperature):
    if 10 <= temperature <= 25:
        return pump_time
    elif 25 < temperature <= 30:
        return pump_time * 1.2
    elif 30 < temperature <= 35:
        return pump_time * 1.5
    elif 5 <= temperature < 10:
        return pump_time * 0.8
    return pump_time

def is_temperature_ok(temperature):
    # You can tune this depending on plant type
    if temperature < 5:
        return False  # Too cold
    if temperature > 35:
        return False  # Too hot
    return True

def adjust_pump_time_by_temperature(pump_time, temperature):
    # Adjust watering time based on evaporation rate or plant need
    if 10 <= temperature <= 25:
        return pump_time  # Ideal
    elif 25 < temperature <= 30:
        return pump_time * 1.2  # Slightly more to compensate evaporation
    elif 30 < temperature <= 35:
        return pump_time * 1.5  # Much more, but risky
    elif 5 <= temperature < 10:
        return pump_time * 0.8  # Less, because plants absorb less
    return pump_time


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
        print(f"Sending message: {message}")
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

    id = combined_hex >> 32
    moisture = combined_hex & 0xFFFFFFFF

    return id, moisture

async def main():
    lora = AsyncLoRaModule()
    db = DatabaseManager(db_path=config.DB_PATH)
    server = config.SERVER_URL
    debug = config.DEBUG
    pump_rate = config.PUMP_RATE

    # Start the timed callback task for periodic updates
    h_update_task = asyncio.create_task(h_callback(db))
    day_update_task = asyncio.create_task(day_callback(db))

    # Debug server management
    #if debug: db.save_sensor(10, "sensor", str(datetime.now()), None)
    #if debug: requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": 10, "role": "sensor", "last_ping": str(datetime.now()), "garden": None})
    #if debug: db.save_sensor(11, "sensor", str(datetime.now()), None)
    #if debug: requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": 11, "role": "sensor", "last_ping": str(datetime.now()), "garden": None})
    #if debug: requests.post(config.SERVER_URL + "new_sensor/" + str(config.RASBERRY_ID), json = {"id": 15, "role": "actuator", "last_ping": str(datetime.now()), "garden": None})
    
    while True:
        try:
            message = await lora.async_receive()
            
            # Uncomment the following line to simulate a message from an actuator for testing purposes
            message = [0,0,0,15,0,0,3,255]

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
                        
                        # Todo: create a method for actuators to streamline the code
                        else:   # Actuator
                            actuators = []
                            for sensor in db.get_sensors():
                                if sensor.get("garden") == garden and sensor.get("role") == "actuator":
                                    actuators.append(sensor.get("id"))

                            if len(actuators) == 0: # Should never happen, but just in case
                                if debug: print("No actuators found for this garden.")
                                try_later(debug, lora, -60 * 24)
                                continue
                            
                            # Get temperature
                            response = requests.post(server + "get_temperature/", json={"garden_id": garden})
                            if response.status_code == 200:
                                temperature = response.json().get("temperature")
                                if debug: print(f"Temperature: {temperature}°C")
                            else:
                                print(f"Error: {response.status_code}")
                                try_later(debug, lora)
                                continue
                            
                            # Season and time
                            season = get_season()
                            now = datetime.now()

                            # Temperature OK?
                            if not is_temperature_ok(temperature):
                                if debug: print(f"Temperature {temperature}°C not suitable for watering. Sleeping until tomorrow.")
                                lora.send(-60 * 60 * 24)  # negative sleep
                                continue
                            
                            # Time OK?
                            if not is_optimal_time(now, season):
                                sleep_time = calculate_sleep_until_optimal(now)
                                if debug: print(f"Not in optimal time window. Sleeping for {-sleep_time} seconds.")
                                lora.send(sleep_time)  # already negative
                                continue
                            
                            # Get water amount
                            response = requests.post(server + "get_water/", json={"garden_id": garden})
                            if response.status_code == 200:
                                water_amount = response.json().get("data")
                                if debug: print(f"Water needed: {water_amount}ml")
                            else:
                                print(f"Error: {response.status_code}")
                                try_later(debug, lora)
                                continue
                            
                            # No water needed?
                            if water_amount == 0:
                                if debug: print("No water needed. Sleeping until tomorrow.")
                                sleep_time = calculate_sleep_until_optimal(now)
                                lora.send(sleep_time)
                                continue
                            
                            # Compute pump time
                            pump_time = water_amount / (pump_rate * len(actuators))
                            pump_time = adjust_pump_time_by_temperature(pump_time, temperature)

                            # Limit pump time to window
                            max_window = (OPTIMAL_END_HOUR - OPTIMAL_START_HOUR) * 3600
                            if pump_time > max_window:
                                if debug: print(f"Pump time {pump_time}s exceeds max window. Reducing to {max_window}s.")
                                pump_time = max_window

                            lora.send(pump_time)

        except asyncio.TimeoutError as e:
            print(f"Timeout occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")