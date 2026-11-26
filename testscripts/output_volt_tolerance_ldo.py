import csv
import os
import subprocess
import sys

from Instrument_drivers.E3631A_powersupply import Supply_E3631A
from Instrument_drivers.MM_34461A import MM_34461A

from Register_Map import functional_register_map

from pyftdi.i2c import I2cController
import argparse
import time

ps = Supply_E3631A()
mm = MM_34461A()

target_volt = [0.75, 1, 1.5, 2]
VLDO = {}
out_volt_tolerance = {}
measurement_data = []


def vldo_code(volts):
    # 0.75 V to 1.50 V: 50 mV steps
    if 0.75 <= volts <= 1.50:
        code = round((volts - 0.75) / 0.05)

        if abs(0.75 + code * 0.05 - volts) < 1e-6:
            return code

    # 1.80 V to 3.30 V: 100 mV steps
    if 1.80 <= volts <= 3.30:
        code = 0x10 + round((volts - 1.80) / 0.10)

        if abs(1.80 + (code - 0x10) * 0.10 - volts) < 1e-6:
            return code

    raise ValueError(
        f"{volts} V is not supported by the LDOx voltage configuration."
    )


Input_Vin = 5.0  # 5V

ps.reset()
ps.set_output('P6V', Input_Vin, 0.2)  # 5V, LIMIT -> 200mA
ps.output_on()
time.sleep(1)

parser = argparse.ArgumentParser()
parser.add_argument("--address", type=lambda x: int(x, 0), default=0x08)
parser.add_argument("--url", default="ftdi://ftdi:232h/1")

args = parser.parse_args()

controller = I2cController()
controller.configure(args.url, frequency=100_000)
port = controller.get_port(args.address)

gpio = controller.get_gpio()

# D4 = bit 4, configure as output
gpio.set_direction(0x10, 0x10)
# PWRON high
gpio.write(0x10)

# Assign the port to the global variable _port, which is used by
# functional_register_map.py for I2C read/write operations via properties.
functional_register_map._port = port

print(f"I2C address: 0x{args.address:02X}")

print("Data present before writing the functional registers:\n")

print(f"DEVICE_ID     : 0x{functional_register_map.DEVICE_ID.value:02X}")
print(f"REV_ID        : 0x{functional_register_map.REV_ID.value:02X}")
print(f"LDO1_PWRUP      : 0x{functional_register_map.LDO1_PWRUP.value:02X}")
print(f"LDO1_CONFIG2    : 0x{functional_register_map.LDO1_CONFIG2.value:02X}")

functional_register_map.LDO1_PWRUP.value = 0x01
functional_register_map.LDO1_CONFIG2.value = 0x82

try:
    for V_out in target_volt:
        # read
        print(f"LDO1_RUN_VOLT  : 0x{functional_register_map.LDO1_RUN_VOLT.value:02X}")
        # write
        functional_register_map.LDO1_RUN_VOLT.value = vldo_code(V_out)
        time.sleep(1)

        mm.reset()
        VLDO[V_out] = float(mm.meas_volt())

        measurement_data.append({
            "Target_Vout": V_out,
            "Input_Vin": Input_Vin,
            "Measured_Vout": VLDO[V_out]
        })

        print("\nLDO output voltage is:", VLDO[V_out], "V")

        out_volt_tolerance[V_out] = ((VLDO[V_out] - V_out) / V_out) * 100
        print(f"\nOutput voltage tolerance %: {out_volt_tolerance[V_out]:.3f} %\n")

finally:
    controller.terminate()
    ps.output_off()
    ps.reset()
    mm.reset()

os.makedirs("results", exist_ok=True)

with open("results/out_volt_tolerance_raw.csv", "w", newline="") as file:
    fieldnames = [
        "Target_Vout",
        "Input_Vin",
        "Measured_Vout"
    ]

    writer = csv.DictWriter(file, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(measurement_data)

print("Raw measurements saved successfully.")

print("\nHardware test completed.")
print("\nStarting post-processing...\n")

post_process_script = os.path.join(
    os.path.dirname(__file__),
    "post_process_out_volt_tolerance_ldo.py"
)

try:
    subprocess.run(
        [sys.executable, post_process_script],
        check=True
    )

    print("\nPost-processing completed successfully.")

except subprocess.CalledProcessError as e:
    print(f"\nPost-processing failed. Error code: {e.returncode}")

except Exception as e:
    print(f"\nError executing post-processing: {e}")
print("\nExiting.\n")