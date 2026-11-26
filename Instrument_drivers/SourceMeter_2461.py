import pyvisa


class SMU_2461:
    def __init__(self, resource_name="USB0::0x05E6::0x2461::04367440::INSTR"):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource_name)
        self.inst.timeout = 5000
        self.inst.write_termination = '\n'
        self.inst.read_termination = '\n'
        idn = self.inst.query("*IDN?")
        print("Instrument ID:", idn)

    def send(self, cmd):
        """Send a SCPI command to the instrument."""
        self.inst.write(cmd)

    def query(self, cmd):
        """Send a command and read back the response."""
        return self.inst.query(cmd)

    def reset(self):
        """Reset the instrument to factory defaults"""
        self.send("*RST")

    def select_volt_func(self):
        """Select Voltage Source function"""
        self.send(":SOUR:FUNC VOLT")

    def select_curr_func(self):
        """Select Current Source function"""
        self.send(":SOUR:FUNC CURR")

    def set_voltage(self, value: float):
        """Set the DC voltage source level"""
        self.send(f":SOUR:VOLT:LEV {value}")

    def set_curr(self, value: float):
        """Set the DC current source level"""
        self.send(f":SOUR:CURR:LEV {value}")

    def compliance_volt(self, compliance):
        """Set voltage compliance limit when sourcing current"""
        self.send(f"SOUR:CURR:VLIM {compliance}")

    def compliance_curr(self, compliance):
        """Set current compliance limit when sourcing voltage"""
        self.send(f"SOUR:VOLT:ILIM {compliance}")

    def source_volt_autorange(self, state=True):
        """Enable/disable auto-ranging on the SOURCE voltage."""
        val = "ON" if state else "OFF"
        self.send(f":SOUR:VOLT:RANG:AUTO {val}")

    def sense_curr_autorange(self, state=True):
        """Enable/disable auto-ranging on the current MEASUREMENT."""
        val = "ON" if state else "OFF"
        self.send(f":SENS:CURR:RANG:AUTO {val}")

    def source_curr_autorange(self, state=True):
        """Enable/disable auto-ranging on the SOURCE current."""
        val = "ON" if state else "OFF"
        self.send(f":SOUR:CURR:RANG:AUTO {val}")


    def sense_volt_autorange(self, state=True):
        """Enable/disable auto-ranging on the voltage MEASUREMENT."""
        val = "ON" if state else "OFF"
        self.send(f":SENS:VOLT:RANG:AUTO {val}")

    def meas_curr(self):

        response = self.query(":MEAS:CURR?")

        if response is None:
            raise ValueError("Instrument returned None")

        return float(response.strip())

    def meas_voltage(self):
        """
        Measure the output voltage.

        Returns:
            float: Measured voltage in volts.
        """
        response = self.query(":MEAS:VOLT?")

        if response is None:
            raise ValueError("Instrument returned None")

        return float(response.strip())

    def on_off_output(self, state=True):
        """Turn the output ON or OFF"""
        val = "ON" if state else "OFF"
        self.send(f":OUTP {val}")

    def rear(self):
        """Route measurements to the rear terminals"""
        self.send("ROUT:TERM REAR")


    def select_volt_measurement(self):
        """Select voltage as the measurement function."""
        self.send(':SENS:FUNC "VOLT"')


    def sense_4W(self):
        """Enable 4-wire Kelvin remote voltage sensing."""
        self.send(":SENS:VOLT:RSEN ON")


