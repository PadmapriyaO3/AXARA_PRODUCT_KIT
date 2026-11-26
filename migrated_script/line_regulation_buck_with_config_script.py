import time

from pyftdi.i2c import I2cController
import functional_register_map

controller: I2cController | None = None


def init(context, harness, logger):
    global controller

    ps = harness.instrument_adapters["power_supply"]

    # Target output voltages
    target_volt = [0.5, 1, 1.5, 2]

    # Input voltage list
    vin_list = [3.5, 4.0, 4.5, 5.0, 5.5]

    # Initialize measurement variables
    line_regulation = {}
    measurement_data = []
    VBUCK = {}

    # Reset PSU
    ps.transact("reset", {})

    # Configure PSU input voltage
    ps.transact(
        "set_output",
        {
            "channel": "P6V",
            "voltage": vin_list[0],
            "current": 0.1,
        },
    )

    ps.transact("output_on", {})

    time.sleep(1)

    # Initialize FT232H I2C controller
    controller = I2cController()

    logger.info("Configuring FT232H")
    controller.configure(
        "ftdi://ftdi:232h/1",
        frequency=100_000
    )

    logger.info("Configuring GPIO")
    gpio = controller.get_gpio()

    # D4 = bit 4, configure as output
    gpio.set_direction(0x10, 0x10)
    gpio.write(0x10)

    # Connect register map to FT232H
    logger.info("Connecting functional register map")
    functional_register_map.connect(port)

    logger.info("I2C address: 0x08")
    logger.info("FT232H controller initialized")

    # Read initial register values
    logger.info("Data present before writing the functional registers:\n")

    logger.info(f"DEVICE_ID: 0x{functional_register_map.DEVICE_ID.read_register():02X}")
    logger.info(f"REV_ID: 0x{functional_register_map.REV_ID.read_register():02X}")
    logger.info(f"INT_SENSE1: 0x{functional_register_map.INT_SENSE1.read_register():02X}")
    logger.info(f"SW1_MODE: 0x{functional_register_map.SW1_MODE.read_register():02X}")

    # Configure functional registers
    functional_register_map.SW1_CONFIG2.write_register(0x09)
    functional_register_map.SW1_MODE.write_register(0x01)
    functional_register_map.SW1_PWRUP.write_register(0x01)

    # Store measurement variables in context
    context.add("target_volt", target_volt)
    context.add("vin_list", vin_list)
    context.add("line_regulation", line_regulation)
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

    ps = harness.instrument_adapters["power_supply"]
    mm = harness.instrument_adapters["multi_meter"]

    # Retrieve variables from context
    target_volt = context.get("target_volt")
    vin_list = context.get("vin_list")

    line_regulation = context.get("line_regulation")
    measurement_data = context.get("measurement_data")
    VBUCK = context.get("VBUCK")

    try:

        for V_out in target_volt:

            VBUCK = {}

            for V in vin_list:
                # Configure PSU input voltage
                ps.transact(
                    "set_output",
                    {
                        "channel": "P6V",
                        "voltage": V,
                        "current": 0.1,
                    },
                )

                time.sleep(1)

                logger.info(f"SW1_RUN_VOLT: 0x{functional_register_map.SW1_RUN_VOLT.read_register():02X}")

                functional_register_map.SW1_RUN_VOLT.write_register(vsw1_code(V_out))

                time.sleep(2)

                # Measure output voltage
                mm.transact("reset", {})

                time.sleep(2)

                response = mm.transact("meas_volt", {})

                VBUCK[str(V)] = response["raw_data"]

                measurement_data.append({
                    "Target_Vout": V_out,
                    "Input_Vin": V,
                    "Measured_Vout": VBUCK[str(V)]
                })

                logger.info(
                    f"Buck output voltage at Vin {V} V: "
                    f"{VBUCK[str(V)]} V"
                )

            # Calculate line regulation
            line_regulation[V_out] = (
                                             (
                                                     VBUCK[V]
                                                     - VBUCK[vin_list[0]]
                                             )
                                             / (vin_list[-1] - vin_list[0])
                                     ) * 100

            logger.info(
                f"Line regulation % in PWM mode at target voltage "
                f"{V_out:.3f} V: {line_regulation[V_out]:.3f} %"
            )

    finally:

        logger.info("Starting hardware cleanup")
        functional_register_map.disconnect()

        if controller is not None:
            controller.terminate()
        logger.info("FT232H controller terminated")
        ps.transact("output_off", {})
        ps.transact("reset", {})
        mm.transact("reset", {})
        logger.info("Hardware cleanup completed")

    # Update context
    context.add("VBUCK", VBUCK)
    context.add("line_regulation", line_regulation)
    context.add("measurement_data", measurement_data)
