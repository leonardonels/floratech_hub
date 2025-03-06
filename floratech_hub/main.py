import asyncio
from floratech_hub.lora.lora import LoRaModule
from floratech_hub.database.tinydb_manager import DatabaseManager
from floratech_hub.server.server_api import ServerAPI
import config

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
    server = ServerAPI(config.SERVER_URL)

    # Create tables if not present (if the software was restarted and the db already exists there is no need to erase the old one)
    # One table for sensors and actuators
        # id
        # role (sensor or actuator)
        # last ping
        # garden
    # One table to record moistures
        # id?
        # timestamp
        # moisture
        # sensor from
        # garden

    # Start the timed callback task for periodic updates
    update_task = asyncio.create_task(timed_callback(server, db))

    while True:
        message = await lora.receive()

        if message:
            # Look for the header of the message
            if message.startswith("sensor"):
                if not db.is_sensor_configured(message):
                    # Configure sensor by answering his ID
                    response = {"id": message}
                    server.send_data(response)
                    
                    # Get updated sensor configuration from server
                    updated_config = await server.get_sensor_config(message)
                    db.update_sensor_configuration(updated_config)
                
                else:
                    # Save moisture into db
                    db.save_moisture(message)

            elif message.startswith("actuator"):
                if not db.is_actuator_configured(message):
                    # Configure actuator by answering his ID
                    response = {"id": message}
                    server.send_data(response)
                    
                    # Get updated sensor configuration from server
                    updated_config = await server.get_sensor_config(message)
                    db.update_actuator_configuration(updated_config)
                
                else:
                    # Read needed water in mm from db
                    needed_water = db.get_needed_water_in_mm()
                    
                    # Compute the time the pump is required to be used
                    if needed_water == 0:
                        # Answer with off state
                        response = {"state": "off"}
                    else:
                        # Compute the time needed
                        duration = compute_pump_duration(needed_water)
                        response = {"state": "on", "duration": duration}
                    
                    # Send response to server
                    server.send_data(response)

        # End this loop iteration by creating a new task waiting for another message
        lora_task = asyncio.create_task(lora.receive())

if __name__ == "__main__":
    asyncio.run(main())