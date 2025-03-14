from tinydb import TinyDB, Query

class DatabaseManager:
    def __init__(self, db_path="/var/lib/floratech/db.json"):
        self.db = TinyDB(db_path)
        self.sensor_table = self.db.table("sensors")
        self.moistures_table = self.db.table("moistures")

    def closedb(self):
        self.db.close()

    def createtable(self, tablename):
        return self.db.table(tablename)

    def insert(table, elem):
        table.insert(elem)

    def printtable(table):
        for sample in table.all():
            print(sample)

    def cleartable(table):
        table.purge()

    def save_sensor(self, id, role, last_ping, garden):
        self.sensor_table.insert({"id": id, "role": role, "last_ping": last_ping, "garden": garden})
    
    def get_sensors(self):
        return self.sensor_table.all()

    def get_sensor(self, id):
        Sensor = Query()
        return self.sensor_table.search(Sensor.id == id)
    
    def get_sensor_by_garden(self, garden):
        Sensor = Query()
        return self.sensor_table.search(Sensor.garden == garden)
    
    def update_sensor(self, id, role, last_ping, garden):
        Sensor = Query()
        self.sensor_table.update({"role": role, "last_ping": last_ping, "garden": garden}, Sensor.id == id)

    def save_moisture(self, timestamp, moisture, sensor_from, garden):
        self.moistures_table.insert({"timestamp": timestamp, "moisture": moisture, "sensor_from": sensor_from, "garden": garden})

    def get_moistures(self):
        return self.moistures_table.all()
    
    def get_moisture_by_garden(self, garden):
        Moisture = Query()
        return self.moistures_table.search(Moisture.garden == garden)
    
    def get_moisture_by_timestamp(self, timestamp):
        Moisture = Query()
        return self.moistures_table.search(Moisture.timestamp == timestamp)
    
    def get_moisture_by_timestamp_range(self, start, end):
        Moisture = Query()
        return self.moistures_table.search((Moisture.timestamp >= start) & (Moisture.timestamp <= end))

    def get_max_sensor_id(self):
        items = self.sensor_table.all()
        ids = [item.get('id') for item in items if 'id' in item]
        return max(ids) if ids else 0