from tinydb import TinyDB, Query

class DatabaseManager:
    def __init__(self, db_path="/var/lib/floratech/db.json"):
        self.db = TinyDB(db_path)

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
