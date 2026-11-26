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

target_volt = [0.5, 1, 1.5, 2]
out_volt_acc = {}
measurement_data = []

def vsw1_code(volts):

    # 0.5 V special code
    if abs(volts - 0.5) < 1e-6:
        return 0x00

    # 0.6 V to 1.35 V: 6.25 mV steps
    if 0.6 <= volts <= 1.35:
        code = round((volts - 0.6) / 0.00625) + 1
        return code

    # 1.45 V special code
    if abs(volts - 1.45) < 1e-6:
        return 0x7D

    # 1.5 V special code
    if abs(volts - 1.5) < 1e-6:
        return 0x7F

    # 1.8 V to 2.5 V: 12.5 mV steps
    if 1.8 <= volts <= 2.5:
        code = 0x80 + round((volts - 1.8) / 0.0125)
        return code

    # 2.6 V special code
    if abs(volts - 2.6) < 1e-6:
        return 0xBB

    # 2.8 V to 3.3 V: 25 mV steps
    if 2.8 <= volts <= 3.3:
        code = 0xC0 + round((volts - 2.8) / 0.025)
        return code

    raise SystemExit(
        f"{volts} V is not supported by the SWx_RUN_VOLT "
    )

Input_Vin = 5.0 #5V

ps.reset()
ps.set_output('P6V', Input_Vin, 0.5) #5V, LIMIT -> 500mA
ps.output_on()
time.sleep(1)

parser = argparse.ArgumentParser()
parser.add_argument("--address", type=lambda x: int(x, 0), default=0x08)
parser.add_argument("--url", default="ftdi://ftdi:232h/1")
args = parser.parse_args()

controller = I2cController()
VBUCK = {}
controller.configure(args.url, frequency=100_000)#100KHz
port = controller.get_port(args.address)

gpio = controller.get_gpio()

# D4 = bit 4, configure as output
gpio.set_direction(0x10, 0x10)
gpio.write(0x10)    # PWRON high

# Connect register map to FT232H
functional_register_map.connect(port)

print(f"I2C address: 0x{args.address:02X}")

print("Data present before writing the functional registers:\n")

print(f"DEVICE_ID     : 0x{functional_register_map.DEVICE_ID.value:02X}")
print(f"REV_ID        : 0x{functional_register_map.REV_ID.value:02X}")
print(f"INT_SENSE1    : 0x{functional_register_map.INT_SENSE1.value:02X}")
print(f"SW1_MODE      : 0x{functional_register_map.SW1_MODE.value:02X}")
print(f"SW1_PWRUP     : 0x{functional_register_map.SW1_PWRUP.value:02X}")

functional_register_map.SW1_CONFIG2.value = 0x09
functional_register_map.SW1_MODE.value = 0x01
functional_register_map.SW1_PWRUP.value = 0x01

try:
    for V_out in target_volt:
            #read
            print(f"SW1_RUN_VOLT  : 0x{functional_register_map.SW1_RUN_VOLT.value:02X}")
            #write
            functional_register_map.SW1_RUN_VOLT.value = vsw1_code(V_out)

            time.sleep(2)
            mm.reset()

            VBUCK[V_out] = float(mm.meas_volt())

            measurement_data.append({
            "Target_Vout": V_out,
            "Input_Vin" : Input_Vin,
            "Measured_Vout": VBUCK[V_out]
            })

            time.sleep(2)
            print("\nBuck output voltage is:", VBUCK[V_out], "V")      

            out_volt_acc[V_out] = ((VBUCK[V_out] - V_out)/V_out)*100
            print(f"\nOutput voltage accuracy % in PWM mode: {out_volt_acc[V_out]:.3f} %\n")

finally:
    functional_register_map.disconnect()
    controller.terminate()
    ps.output_off()
    ps.reset()
    mm.reset()

os.makedirs("results", exist_ok=True)

with open("results/output_volt_acc_buck_raw.csv", "w", newline="") as file:

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
print("Starting post-processing...\n")

post_process_script = os.path.join(
    os.path.dirname(__file__),
    "post_process_output_volt_acc_buck.py"
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
print("Exiting.\n")