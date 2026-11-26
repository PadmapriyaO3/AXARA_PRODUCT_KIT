import time


def init(context, harness):

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

    # Store variables in context
    context.add("vin_list", vin_list)
    context.add("target_volt", target_volt)
    context.add("Input_Vin", Input_Vin)
    context.add("VLDO", VLDO)
    context.add("line_regulation", line_regulation)
    context.add("measurement_data", measurement_data)
