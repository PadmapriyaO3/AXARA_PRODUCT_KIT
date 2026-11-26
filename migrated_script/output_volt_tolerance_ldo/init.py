import time


def init(context, harness):

    # Get instruments from Harness
    ps = harness.instrument_adapters["power_supply"]

    target_volt = [0.75, 1, 1.5, 2]
    VLDO = {}
    out_volt_tolerance = {}
    measurement_data = []

    Input_Vin = 5.0  # 5V

    ps.transcat("reset", {})
    ps.transcat("set_output", {"channel": 'P6V', "voltage": Input_Vin, "current": 0.2})  # 5V, LIMIT -> 200mA
    ps.transcat("output_on", {})
    time.sleep(1)

    context.add("target_volt", target_volt)
    context.add("VLDO", VLDO)
    context.add("out_volt_tolerance", out_volt_tolerance)
    context.add("measurement_data", measurement_data)