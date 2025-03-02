import spidev
from gpiozero import OutputDevice, InputDevice
from time import sleep, time
from lora.constants import REG, MODE

class LoRaModule:
    def __init__(self, cs_pin=25, rst_pin=22, dio0_pin=27, dio1_pin=24, frequency=8000000, debug=False):
        self.debug = debug
        self.cs_pin = OutputDevice(cs_pin)
        self.reset_pin = OutputDevice(rst_pin)
        self.dio0_pin = InputDevice(dio0_pin) if dio0_pin else None
        self.dio1_pin = InputDevice(dio1_pin) if dio1_pin else None
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = frequency
    
    def _write_register(self, address, data):
        self.cs_pin.off()
        self.spi.writebytes([address | 0x80, data])
        self.cs_pin.on()
        sleep(0.015)
    
    def _read_register(self, address):
        self.cs_pin.off()
        self.spi.writebytes([address & 0x7F])
        response = self.spi.readbytes(1)
        self.cs_pin.on()
        return response[0]

    def reset(self):
        self.reset_pin.off()
        sleep(0.1)
        self.reset_pin.on()
    
    def begin(self, frequency=433, bandwidth=0x90, spreading_factor=0x70, coding_rate=0x02, rx_crc=False, xosc_freq=32):
        self.reset()
        sleep(0.1)
        self._write_register(REG.LORA.OP_MODE, MODE.SLEEP)
        while self._read_register(REG.LORA.OP_MODE) != MODE.SLEEP:
            print("Error initiating the LoRa module, wait...")
            sleep(5)
            self._write_register(REG.LORA.OP_MODE, MODE.SLEEP)
        self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
        
        frf = int((frequency * (2**19)) / xosc_freq)
        self._write_register(REG.LORA.FR_MSB, (frf >> 16) & 0xFF)
        self._write_register(REG.LORA.FR_MID, (frf >> 8) & 0xFF)
        self._write_register(REG.LORA.FR_LSB, frf & 0xFF)
        
        self._write_register(REG.LORA.MODEM_CONFIG_1, bandwidth | coding_rate)
        self._write_register(REG.LORA.MODEM_CONFIG_2, spreading_factor | 0x04 * rx_crc)
        sleep(1)
    
    def send(self, message):
        while self._activity_detection(0.01):
            print("Preamble detected, waiting...")
            sleep(0.01)
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_TX_BASE_ADDR))
        for byte in message.encode():
            self._write_register(REG.LORA.FIFO, byte)
        self._write_register(REG.LORA.PAYLOAD_LENGTH, len(message))
        self._write_register(REG.LORA.OP_MODE, MODE.TX)
        print(f"Message sent: {message}")
    
    def receive(self, timeout=5):
        self._set_module_on_receive()
        start_time = time()
        while True:
            if self.dio0_pin.is_active:
                return self._on_receive()
            if (time() - start_time > timeout) and timeout != 0:
                self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
                return "Timeout: No messages received."

    def _on_receive(self):
        nb_bytes = self._read_register(REG.LORA.RX_NB_BYTES)
        message = ''.join(chr(self._read_register(REG.LORA.FIFO)) for _ in range(nb_bytes))
        self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
        self._write_register(REG.LORA.OP_MODE, MODE.RXCONT)
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_RX_BASE_ADDR))
        self._write_register(REG.LORA.IRQ_FLAGS, 0xFF)
        return message

    def _activity_detection(self, timeout=0):
        start_time = time()
        while True:
            self._write_register(REG.LORA.DIO_MAPPING_1, 0x20)
            self._write_register(REG.LORA.OP_MODE, MODE.CAD)
            if self.dio1_pin and self.dio1_pin.is_active:
                return True
            if (time() - start_time > timeout) and timeout != 0:
                self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
                return False
    
    def _set_module_on_receive(self):
        if self._read_register(REG.LORA.DIO_MAPPING_1) != 0x00:
            self._write_register(REG.LORA.DIO_MAPPING_1, 0x00)
        self._write_register(REG.LORA.OP_MODE, MODE.RXCONT)
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_RX_BASE_ADDR))
    
    def close(self):
        if self.spi:
            self.spi.close()
