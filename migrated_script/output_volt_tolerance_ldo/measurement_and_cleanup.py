import time
from pyftdi.i2c import I2cController
import functional_register_map

from testscripts.output_volt_tolerance_ldo import out_volt_tolerance

# Global controller object
controller: I2cController | None = None

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


def measurement_and_cleanup(context, harness, logger):

    # Get instruments from Harness
    ps = harness.instrument_adapters["power_supply"]
    mm = harness.instrument_adapters["multi_meter"]

    # Initialize FT232H I2C controller
    controller = I2cController()
    controller.configure("ftdi://ftdi:232h/1", frequency=100_000)
    port = controller.get_port(0x08)

    gpio = controller.get_gpio()

    # D4 = bit 4, configure as output
    gpio.set_direction(0x10, 0x10)
    # PWRON high
    gpio.write(0x10)

    # Assign the port to the global variable _port, which is used by
    # functional_register_map.py for I2C read/write operations via properties.
    functional_register_map._port = port

    logger.info(f"I2C address: 0x08")

    logger.info("Data present before writing the functional registers:\n")

    logger.info(f"DEVICE_ID     : 0x{functional_register_map.DEVICE_ID.read_register():02X}")
    logger.info(f"REV_ID        : 0x{functional_register_map.REV_ID.read_register():02X}")
    logger.info(f"LDO1_PWRUP      : 0x{functional_register_map.LDO1_PWRUP.read_register():02X}")
    logger.info(f"LDO1_CONFIG2    : 0x{functional_register_map.LDO1_CONFIG2.read_register():02X}")

    functional_register_map.LDO1_PWRUP.write_register(0x01)
    functional_register_map.LDO1_CONFIG2.write_register(0x82)

    target_volt = context.get("target_volt")
    VLDO = context.get("VLDO")
    measurement_data = context.get("measurement_data")
    Input_Vin = context.get("Input_Vin")
    out_volt_tolerance = context.get("out_volt_tolerance")

    try:
        for V_out in target_volt:
            # read
            logger.info(f"LDO1_RUN_VOLT  : 0x{functional_register_map.LDO1_RUN_VOLT.read_register():02X}")
            # write
            functional_register_map.LDO1_RUN_VOLT.write_register(vldo_code(V_out))
            time.sleep(1)

            mm.transcat("reset", {})
            response = mm.transcat("meas_volt", {})
            VLDO[V_out] = float(response)

            measurement_data.append({
                "Target_Vout": V_out,
                "Input_Vin": Input_Vin,
                "Measured_Vout": VLDO[str(V_out)]
            })

            logger.info(f"\nLDO output voltage is: {VLDO[str(V_out)]} V")

            out_volt_tolerance[V_out] = ((VLDO[str(V_out)] - V_out) / V_out) * 100
            logger.info(f"\nOutput voltage tolerance %: {out_volt_tolerance[str(V_out)]:.3f} %\n")

    finally:
        controller.terminate()
        ps.transcat("output_off", {})
        ps.transcat("reset", {})
        mm.transcat("reset", {})