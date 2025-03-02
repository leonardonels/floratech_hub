import unittest
from floratech_hub.lora.lora import LoRaModule

class TestLoRa(unittest.TestCase):
    def test_init(self):
        lora = LoRaModule()
        self.assertIsNotNone(lora)

if __name__ == "__main__":
    unittest.main()
