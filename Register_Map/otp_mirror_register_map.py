import json
from pathlib import Path
import time

# Load JSON register map
JSON_PATH = Path(__file__).with_name("otp_mirror_register_map.json")

with open(JSON_PATH, "r") as file:
    _register_data = json.load(file)

# Create register lookup

if isinstance(_register_data, dict):
    
    register_list = next(
            (value for value in _register_data.values() if isinstance(value, list)),
            None
        )

    if register_list is None:
            raise ValueError("No register list found in JSON")

else:
    raise TypeError("Unsupported JSON structure")

_registers = {
    reg["name"].upper(): reg["address"]
    for reg in register_list
}

# FT232H I2C port
_port = None

# Verification delay
VERIFY_DELAY = 0.05

def connect(port):
    global _port

    if port is None:
        raise ValueError("Invalid I2C port")

    _port = port
    print("OTP mirror register map connected.")


def disconnect():
    global _port
    _port = None


class Register:

    def __init__(self, name, address):
        self.name = name
        self.address = address

    @property
    def value(self):

        if _port is None:
            raise RuntimeError("Register map is not connected to FT232H")

        data = _port.exchange(bytes([self.address]), 1)[0]

        return data

    @value.setter
    def value(self, data):

        if _port is None:
            raise RuntimeError("Register map is not connected to FT232H")

        if not isinstance(data, int) or not 0 <= data <= 0xFF:
            raise ValueError("Register data must be an integer between 0x00 and 0xFF")

        # Write register
        _port.write_to(self.address, bytes([data]))

        time.sleep(VERIFY_DELAY)
        
        # Readback verification
        readback = _port.exchange(bytes([self.address]), 1)[0]

        status = "OK" if readback == data else "MISMATCH"

        print(
            f"WRITE {self.name:14} "
            f"0x{self.address:02X} <- 0x{data:02X} | "
            f"READBACK 0x{readback:02X} [{status}]"
        )

        if readback != data:
            raise IOError(f"Write verification failed for {self.name}")


# Dynamically access registers using their names
def __getattr__(name):

    register_name = name.upper()

    if register_name in _registers:
        return Register(register_name, _registers[register_name])

    raise AttributeError(f"Register '{name}' not found in otp mirror register map")

