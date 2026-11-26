
import time

from pyftdi.i2c import I2cController
import functional_register_map

# Global controller object
controller: I2cController | None = None


def init(context, harness, logger):

    global controller

    # Get instruments from Harness
    ps = harness.instrument_adapters["power_supply"]
    mm = harness.instrument_adapters["multi_meter"]

    # Input voltage sweep
    vin_list = [3.5, 4.0, 4.5, 5.0, 5.5]

    # Target LDO output voltages
    target_volt = [0.75, 1, 1.5, 2]

    # Initial input voltage
    Input_Vin = 5.0

    # Initialize measurement variables
    VLDO = {}
    line_regulation = {}
    measurement_data = []

    # Configure PSU
    ps.transact("reset", {})

    ps.transact(
        "set_output",
        {
            "channel": "P6V",
            "voltage": Input_Vin,
            "current": 0.2,
        },
    )

    ps.transact("output_on", {})

    time.sleep(1)

    # Reset multimeter
    mm.transact("reset", {})

    time.sleep(2)

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

    # PWRON high
    gpio.write(0x10)

    # Connect register map to FT232H
    functional_register_map.connect(port)

    logger.info("I2C address: 0x08")

    # Read initial register values
    logger.info("Data present before writing the functional registers:")

    logger.info(f"DEVICE_ID       : 0x{functional_register_map.DEVICE_ID.read_register():02X}")
    logger.info(f"REV_ID          : 0x{functional_register_map.REV_ID.read_register():02X}")
    logger.info(f"LDO1_PWRUP      : 0x{functional_register_map.LDO1_PWRUP.read_register():02X}")
    logger.info(f"LDO1_CONFIG2    : 0x{functional_register_map.LDO1_CONFIG2.read_register():02X}")

    # Configure functional registers
    functional_register_map.LDO1_PWRUP.write_register(0x01)
    functional_register_map.LDO1_CONFIG2.write_register(0x82)

    # Store variables in context
    context.add("vin_list", vin_list)
    context.add("target_volt", target_volt)
    context.add("Input_Vin", Input_Vin)
    context.add("VLDO", VLDO)
    context.add("line_regulation", line_regulation)
    context.add("measurement_data", measurement_data)


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

    global controller

    # Get instruments from Harness
    mm = harness.instrument_adapters["multi_meter"]
    ps = harness.instrument_adapters["power_supply"]

    # Retrieve variables from context
    vin_list = context.get("vin_list")
    target_volt = context.get("target_volt")

    VLDO = context.get("VLDO")
    line_regulation = context.get("line_regulation")
    measurement_data = context.get("measurement_data")

    try:

        for V_out in target_volt:

            # Read register
            logger.info(f"LDO1_RUN_VOLT : 0x{functional_register_map.LDO1_RUN_VOLT.read_register():02X}")

            # Write register
            functional_register_map.LDO1_RUN_VOLT.write_register(vldo_code(V_out))

            logger.info(f"Target output voltage set as: {V_out:.3f} V")

            # Initialize measurements for current target voltage
            VLDO[V_out] = {}

            for V in vin_list:

                # Set input voltage
                ps.transact(
                    "set_output",
                    {
                        "channel": "P6V",
                        "voltage": V,
                        "current": 0.1,
                    },
                )

                time.sleep(1)

                # Measure LDO output voltage
                response = mm.transact("meas_volt", {})

                VLDO[V] = float(response["raw_data"])

                measurement_data.append({
                    "Target_Vout": V_out,
                    "Input_Vin": V,
                    "Measured_Vout": VLDO[V_out][V]
                })

                logger.info(
                    f"LDO output voltage at V_in: {V:.3f} V "
                    f"is: {VLDO[V_out][V]:.6f} V"
                )

            # Calculate line regulation
            line_regulation[V_out] = ((VLDO[str(V)] - VLDO[str(vin_list[0])])/ (vin_list[-1] - vin_list[0])) * 100

            logger.info(
                f"Line regulation % at target voltage: "
                f"{V_out:.3f} V is: "
                f"{line_regulation[V_out]:.3f} %"
            )

    finally:

        functional_register_map.disconnect()

        if controller is not None:
            controller.terminate()

        ps.transact("output_off", {})
        ps.transact("reset", {})
        mm.transact("reset", {})

    # Update context
    context.add("VLDO", VLDO)
    context.add("line_regulation", line_regulation)
    context.add("measurement_data", measurement_data)

    logger.info("Cleanup completed")
