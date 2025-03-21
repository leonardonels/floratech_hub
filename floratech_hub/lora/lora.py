import spidev
from gpiozero import OutputDevice, InputDevice, Button
from time import sleep, time
from lora.constants import REG, MODE
import struct

class LoRaModule():
    def __init__(self):
        self._debugger = False
        self._cs_pin = None
        self._reset_pin = None
        self._dio0_pin = None
        self._dio1_pin = None
        self._spi = None

        self.setup()
        self.begin()

    def setup(self, cs_pin_number=25, rst_pin_number=22, dio0_pin_number=27, dio1_pin_number=24, frequency=8000000, debug=False):

        #set debug mode
        self._debugger = debug

        # Imposta i pin
        self._cs_pin = OutputDevice(cs_pin_number)
        self._reset_pin = OutputDevice(rst_pin_number)
        if dio0_pin_number != False:
            self._dio0_pin = InputDevice(dio0_pin_number)
        if dio1_pin_number != False:
            self._dio1_pin = InputDevice(dio1_pin_number)

        # Imposta SPI
        self._spi = spidev.SpiDev()
        self._spi.open(0, 0)
        self._spi.max_speed_hz = frequency

    def reset_lora(self):
        self._reset_pin.off()
        sleep(0.1)
        self._reset_pin.on()

    def async_dio0(dio_pin):
        return Button(dio_pin)

    def async_dio1(dio_pin):
        return Button(dio_pin)

    def close(self):
        if self._spi is not None:
            self._spi.close()

    def _write_register(self, address, data):
        self._cs_pin.off()
        self._spi.writebytes([address | 0x80, data])
        self._cs_pin.on()
        sleep(0.015)

    def _read_register(self, address):
        self._cs_pin.off()
        self._spi.writebytes([address & 0x7F])
        response = self._spi.readbytes(1)
        self._cs_pin.on()
        return response[0]
    
    def set_mode(self, mode):
        self._write_register(REG.LORA.OP_MODE, mode)

    def begin(self, frequency=433, hex_bandwidth=0x90, hex_spreading_factor=0x70, hex_coding_rate=0x02, rx_crc=True, xosc_freq=32):
        self.reset_lora()
        sleep(0.1)

        self._write_register(REG.LORA.OP_MODE, MODE.SLEEP)
        while self._read_register(REG.LORA.OP_MODE)!=MODE.SLEEP:
            print("Error initiating the LoRa module, wait...")
            sleep(5)
            self._write_register(REG.LORA.OP_MODE, MODE.SLEEP)
        self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
        if(self._debugger):print(f"BEGIN_OP_MODE: {self._read_register(REG.LORA.OP_MODE)}")
        self._write_register(REG.LORA.PA_CONFIG, 0x8F)

        frf = int((frequency * (2**19)) / xosc_freq)
        msb = (frf >> 16) & 0xFF
        mid = (frf >> 8) & 0xFF
        lsb = frf & 0xFF

        self._write_register(REG.LORA.FR_MSB, msb)
        self._write_register(REG.LORA.FR_MID, mid)
        self._write_register(REG.LORA.FR_LSB, lsb)

        self._write_register(REG.LORA.MODEM_CONFIG_1, hex_bandwidth | hex_coding_rate)
        self._write_register(REG.LORA.MODEM_CONFIG_2, hex_spreading_factor | 0x04*rx_crc)
        self._write_register(REG.LORA.DIO_MAPPING_1, 0x00) #DIO_MAPPING_RX
        self._write_register(REG.LORA.DETECT_OPTIMIZE, 0x83)
        self._write_register(REG.LORA.LNA, 0x23)
        sleep(1)

    def send_bytes(self, byte_message):
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_TX_BASE_ADDR))
        for byte in byte_message:
            self._write_register(REG.LORA.FIFO, byte)
        self._write_register(REG.LORA.PAYLOAD_LENGTH, len(byte_message))
        self._write_register(REG.LORA.OP_MODE, MODE.TX)
        if(self._debugger):print(f"SEND_OP_MODE: {self._read_register(REG.LORA.OP_MODE)}")

    def send(self, message):
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_TX_BASE_ADDR))
        for byte in message.encode():
            self._write_register(REG.LORA.FIFO, byte)
        self._write_register(REG.LORA.PAYLOAD_LENGTH, len(message))
        self._write_register(REG.LORA.OP_MODE, MODE.TX)
        if(self._debugger):print(f"SEND_OP_MODE: {self._read_register(REG.LORA.OP_MODE)}")
        print(f"{message} sent.")

    def send_id(self, message):
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_TX_BASE_ADDR))
        number_bytes = struct.pack('<I', message)
        for byte in number_bytes:
            print(byte)
            self._write_register(REG.LORA.FIFO, byte)
        self._write_register(REG.LORA.PAYLOAD_LENGTH, 4)
        self._write_register(REG.LORA.OP_MODE, MODE.TX)
        print(f"Message sent: {message}")

    def receive(self, timeout=5):
        self.set_module_on_receive()
        start_time = time()
        while True:
            if self._dio0_pin.is_active:
                message = self.on_receive()
                start_time = time()
                return message
            elif (time() - start_time > timeout) & timeout!=0:
                self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
                return "Timeout: No messages received within the specified time."

    def set_module_on_receive(self):
        if self._read_register(REG.LORA.DIO_MAPPING_1) != 0x00:
            self._write_register(REG.LORA.DIO_MAPPING_1, 0x00)
        self._write_register(REG.LORA.OP_MODE, MODE.RXCONT)
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_RX_BASE_ADDR))

    def on_receive(self):
        nb_bytes = self._read_register(REG.LORA.RX_NB_BYTES)
        message = [self._read_register(REG.LORA.FIFO) for _ in range(nb_bytes)]
        reconstructed_message = ''.join(chr(byte) for byte in message)
        self._write_register(REG.LORA.OP_MODE, MODE.STDBY)
        self._write_register(REG.LORA.OP_MODE, MODE.RXCONT)
        self._write_register(REG.LORA.FIFO_ADDR_PTR, self._read_register(REG.LORA.FIFO_RX_BASE_ADDR))
        self._write_register(REG.LORA.IRQ_FLAGS, 0xFF)
        return reconstructed_message