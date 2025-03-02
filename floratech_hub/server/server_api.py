import requests

class ServerAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    def send_data(self, data):
        response = requests.post(f"{self.base_url}/upload", json=data)
        return response.json()

    def get_commands(self):
        response = requests.get(f"{self.base_url}/commands")
        return response.json()
