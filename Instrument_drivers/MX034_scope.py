import time

import pyvisa

class MX034SCOPE:
    def __init__(self, resource_string="USB0::0x0AAD::0x0197::1335.2050k04-102093::INSTR", timeout=5000):
        rm = pyvisa.ResourceManager()
        self.scope = rm.open_resource(resource_string)
        self.scope.timeout = timeout
        idn = self.scope.query("*IDN?")
        print("Instrument ID:", idn)
    
    def write(self,cmd):
        
        self.scope.write(cmd)

    def reset(self):
        """Reset the oscilloscope to default settings."""
        self.scope.write("*RST")

    def configure_channel(self, channel=1, state=True, coupling="DC", bandwidth="B20", scale=0.02):
        """
        Configure a channel.
        scale is in volts/div. Example: 0.02 = 20 mV/div
        """
        self.scope.write(f"CHAN{channel}:STAT {'ON' if state else 'OFF'}")
        self.scope.write(f"CHAN{channel}:COUP {coupling}")
        self.scope.write(f"CHANnel{channel}:BANDwidth {bandwidth}")
        self.scope.write(f"CHAN{channel}:SCAL {scale}")


    def configure_timebase(self, scale=1e-6):
        """Set the horizontal time scale (s/div)."""
        self.scope.write(f"TIM:SCAL {scale}")

    def configure_acquisition(self):
        self.scope.write("ACQuire:TYPE AVERage")
        self.scope.write("ACQuire:COUNt 64")   # number of waveforms to average, e.g. 16-64

    def run_continuous(self):
        """Start continuous acquisition (RUN mode)."""
        self.scope.write("RUN")

    def stop(self):
        """Stop acquisition."""
        self.scope.write("STOP")

    def set_trigger(self, channel=1,slope="POSitive"):
        self.scope.write(f"TRIGger:EVENt1:SOURce C{channel}")
        self.scope.write("TRIGger:EVENt1:TYPE ANEDge")
        self.scope.write(f"TRIGger:EVENt1:EDGE:SLOPe {slope}")

    def enable_statistics(self, channel=1):
        """Enable statistics for a measurement slot."""
        self.scope.write(f"MEAS{channel}:STAT ON")

    def configure_measurement(self, ch: int, meas_index: int = 1):
    # PDELta = High - Low = peak-to-peak amplitude measurement on the MXO series.
        self.scope.write(f"MEASurement{meas_index}:SOURce CH{ch}")
        self.scope.write(f"MEASurement{meas_index}:MAIN PDELta")
        self.scope.write(f"MEASurement{meas_index}:ENABle ON")

    def run_and_measure(self, meas_index: int = 1):
        self.scope.write("RUN")
        time.sleep(2)
        self.scope.write("SINGle")
        self.scope.query("*OPC?")  # blocks until acquisition completes
        result_v = float(self.scope.query(f"MEASurement{meas_index}:RESult:ACTual?"))
        return result_v

    def get_overshoot_voltage(self, slot):
        """
        slot: analog channel number to measure (e.g. 1 -> C1)
        Uses measurement slot 1 (MEASurement1) on the MXO34.
        """
        time.sleep(1)
        self.scope.write(f"MEASurement1:SOURce C{slot}")
        self.scope.write("MEASurement1:MAIN UPEakvalue")
        self.scope.write("MEASurement1:ENABle ON")
        time.sleep(1)
        Vpos_peak = float(self.scope.query("MEASurement1:RESult:ACTual?"))

        time.sleep(2)
        self.scope.write("MEASurement1:MAIN HIGH")
        time.sleep(1)
        vtop = float(self.scope.query("MEASurement1:RESult:ACTual?"))

        time.sleep(2)
        overshoot_volts_mV = (abs(Vpos_peak - vtop))*1000
        return overshoot_volts_mV
    
    def get_undershoot_voltage(self, slot):
        """
        slot: analog channel number to measure (e.g. 1 -> C1)
        Uses measurement slot 1 (MEASurement1) on the MXO34.
        """
        time.sleep(1)
        self.scope.write(f"MEASurement1:SOURce C{slot}")
        self.scope.write("MEASurement1:MAIN LPEakvalue")
        self.scope.write("MEASurement1:ENABle ON")
        time.sleep(1)
        Vneg_peak = float(self.scope.query("MEASurement1:RESult:ACTual?"))

        time.sleep(2)
        self.scope.write("MEASurement1:MAIN LOW")
        time.sleep(1)
        vbottom = float(self.scope.query("MEASurement1:RESult:ACTual?"))

        time.sleep(2)
        undershoot_volts_mV = (abs(vbottom - Vneg_peak))*1000
        return undershoot_volts_mV

    def close(self):
        """Close VISA session."""
        self.scope.close()



