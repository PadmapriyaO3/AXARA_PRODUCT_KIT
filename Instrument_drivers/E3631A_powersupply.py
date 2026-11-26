import pyvisa

class Supply_E3631A:
    def __init__(self, resource_name="GPIB1::1::INSTR"):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource_name)
        self.inst.timeout = 5000
        self.inst.write_termination = '\n'
        self.inst.read_termination = '\n'
        idn = self.inst.query("*IDN?")
        print("Instrument ID:", idn)

    def identify(self):
        return self.inst.query("*IDN?").strip()

    def reset(self):
        self.inst.write("*RST")

    def select_channel(self, channel: str):
        """
        Select output channel.
        Valid options: 'P6V', 'P25V', 'N25V'
        """
        if channel not in ["P6V", "P25V", "N25V"]:
            raise ValueError("Channel must be 'P6V', 'P25V', or 'N25V'.")
        self.inst.write(f"INSTrument:SELect {channel}")

    def set_output(self, channel: str, voltage: float = None, current: float = None):
        """
        Set voltage and/or current limit for a given channel.
        Both are optional; you can set one or both.
        """
        self.select_channel(channel)
        if voltage is not None:
            self.inst.write(f"VOLT {voltage}")
        if current is not None:
            self.inst.write(f"CURR {current}")

    def set_compliance(self, channel: str, volt_limit: float = None, curr_limit: float = None):
        """
        Set compliance limits (absolute maximums).
        For E3631A: only voltage protection is supported.
        Current limit is set normally, not as 'protection'.
        """
        self.select_channel(channel)
        if volt_limit is not None:
            self.inst.write(f"VOLT:PROT {volt_limit}")   # Voltage protection/compliance
        if curr_limit is not None:
            self.inst.write(f"CURR {curr_limit}")        # Current limit (not compliance/protection)


    def output_on(self):
        self.inst.write("OUTP ON")
        print("Output is ON")

    def output_off(self):
        self.inst.write("OUTP OFF")
        print("Output is OFF")