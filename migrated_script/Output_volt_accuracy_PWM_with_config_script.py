import time

from pyftdi.i2c import I2cController
import functional_register_map

# Global controller object
controller: I2cController | None = None

def init(context, harness, logger):

    global controller

    # Get instruments from Harness
    ps = harness.instrument_adapters["power_supply"]

    # Target output voltages
    target_volt = [0.5, 1, 1.5, 2]

    # Input voltage
    Input_Vin = 5.0  # 5V

    # Initialize measurement variables
    out_volt_acc = {}
    measurement_data = []
    VBUCK = {}

    # Configure PSU
    ps.transact("reset", {})
    ps.transact(
        "set_output",
        {
            "channel": "P6V",
            "voltage": Input_Vin,
            "current": 0.5,
        },
    )
    ps.transact("output_on", {})

    time.sleep(1)

    # Initialize FT232H I2C controller
    controller = I2cController()

    controller.configure(
        "ftdi://ftdi:232h/1",
        frequency=100_000
    )

    port = controller.get_port(0x08)

    gpio = controller.get_gpio()

    # D4 = bit 4, configure as output
    gpio.set_direction(0x10, 0x10)
    gpio.write(0x10)  # PWRON high

    # Connect register map to FT232H
    functional_register_map.connect(port)

    logger.info("I2C address: 0x08")

    # Read initial register values
    logger.info("Data present before writing the functional registers:\n")

    logger.info(f"DEVICE_ID     : 0x{functional_register_map.DEVICE_ID.read_register():02X}")
    logger.info(f"REV_ID        : 0x{functional_register_map.REV_ID.read_register():02X}")
    logger.info(f"INT_SENSE1    : 0x{functional_register_map.INT_SENSE1.read_register():02X}")
    logger.info(f"SW1_MODE      : 0x{functional_register_map.SW1_MODE.read_register():02X}")
    logger.info(f"SW1_PWRUP     : 0x{functional_register_map.SW1_PWRUP.read_register():02X}")

    # Configure functional registers
    functional_register_map.SW1_CONFIG2.write_register(0x09)
    functional_register_map.SW1_MODE.write_register(0x01)
    functional_register_map.SW1_PWRUP.write_register(0x01)

    # Store variables in context
    context.add("target_volt", target_volt)
    context.add("Input_Vin", Input_Vin)
    context.add("out_volt_acc", out_volt_acc)
    context.add("measurement_data", measurement_data)
    context.add("VBUCK", VBUCK)


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

        raise ValueError(
            f"{volts} V is not supported by the SWx_RUN_VOLT"
        )

def measurement_and_cleanup(context, harness, logger):

    global controller

    # Get multimeter from Harness
    mm = harness.instrument_adapters["multi_meter"]
    ps = harness.instrument_adapters["power_supply"]

    # Retrieve variables from context
    target_volt = context.get("target_volt")
    Input_Vin = context.get("Input_Vin")

    out_volt_acc = context.get("out_volt_acc")
    measurement_data = context.get("measurement_data")
    VBUCK = context.get("VBUCK")



    try:
        for V_out in target_volt:

            # Read register
            logger.info(
                f"SW1_RUN_VOLT  : "
                f"0x{functional_register_map.SW1_RUN_VOLT.read_register():02X}"
            )

            # Write register
            functional_register_map.SW1_RUN_VOLT.write_register(
                vsw1_code(V_out)
            )

            time.sleep(2)

            mm.transact("reset", {})

            response = mm.transact("meas_volt", {})

            VBUCK[V_out] = response["raw_data"]

            measurement_data.append({
                "Target_Vout": V_out,
                "Input_Vin": Input_Vin,
                "Measured_Vout": VBUCK[V_out]
            })

            time.sleep(2)

            logger.info("\nBuck output voltage is:", VBUCK[V_out], "V")

            out_volt_acc[V_out] = (
                (VBUCK[V_out] - V_out) / V_out
            ) * 100

            logger.info(
                f"\nOutput voltage accuracy % in PWM mode: "
                f"{out_volt_acc[V_out]:.3f} %\n"
            )

    finally:
        functional_register_map.disconnect()
        if controller is not None:
            controller.terminate()
        ps.transact("output_off",{})
        ps.transact("reset", {})
        mm.transact("reset", {})

    # Update context
    context.add("VBUCK", VBUCK)
    context.add("out_volt_acc", out_volt_acc)
    context.add("measurement_data", measurement_data)
    logger.info("Cleanup completed")

