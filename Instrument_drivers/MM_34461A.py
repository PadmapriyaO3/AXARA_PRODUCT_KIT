import pyvisa


class MM_34461A:
    def __init__(self, resource_name='USB0::0x2A8D::0x1401::MY57212733::INSTR'):
        
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource_name)
        self.inst.timeout = 10000
        print("Instrument ID:",self.inst.query("*IDN?"))

    def meas_volt(self):

        return float(self.inst.query("MEAS:VOLT:DC?"))
 
    def meas_curr(self):

        return float(self.inst.query("MEAS:CURR:DC?"))
 
    # def autorange_volt(self,state):

    #     return float(self.inst.query(f'SENS:VOLT:DC:RANG:AUTO {state.upper()}'))
 
    # def autorange_curr(self,state):

    #     return float(self.inst.query(f'SENS:CURR:DC:RANG:AUTO {state.upper()}'))

    def sense4W_ohm(self):

        return float(self.inst.query('SENS:FUNC "FRES"'))
 
    def sense2W_ohm(self):

        return float(self.inst.query('SENS:FUNC "RES"'))
 
    def reset(self):

        self.inst.write("*RST")

        self.inst.write("*CLS")
 
    def close(self):

        self.inst.close()

        # self.rm.close()

    # def average_curr(self,COUNT,DELAY=0.1):

    #     time.sleep(DELAY)
    #     self.inst.write('CONF:CURR:DC')
    #     time.sleep(DELAY)
    #     self.inst.write('CALC:FUNC AVER')
    #     time.sleep(DELAY)
    #     self.inst.write('CALC:STAT ON')
    #     time.sleep(DELAY)
    #     self.inst.write(f'SAMP:COUN {COUNT}')
    #     time.sleep(DELAY)
    #     self.inst.write('INIT')
    #     time.sleep(DELAY)
    #     return float(self.inst.write("CALC:AVER:AVER?"))



    # def config_dc_current(self):
    #     self.inst.write('CONF:CURR:DC')

    # def set_average_function(self):
    #     self.inst.write('CALC:FUNC AVER')

    # def enable_average(self):
    #     self.inst.write('CALC:STAT ON')

    # def disable_average(self):
    #     self.inst.write('CALC:STAT OFF')

    # def set_sample_count(self, count):
    #     self.inst.write(f'SAMP:COUN {count}')

    # def initiate_measurement(self):
    #     self.inst.write('INIT')

    # def read_average_current(self):
    #     return float(self.inst.query('CALC:AVER:AVER?'))
    
    # def average_curr(self, COUNT, DELAY=0.2):

    #     self.config_dc_current()
    #     time.sleep(DELAY)

    #     self.set_average_function()
    #     time.sleep(DELAY)

    #     self.enable_average()
    #     time.sleep(DELAY)

    #     self.set_sample_count(COUNT)
    #     time.sleep(DELAY)

    #     self.initiate_measurement()
    #     time.sleep(DELAY)

    #     return self.read_average_current()
    def average_curr(self, count, delay=0.5):

        self.inst.write('CONF:CURR:DC')
        self.inst.write('CALC:FUNC AVER')
        self.inst.write('CALC:STAT ON')
        self.inst.write(f'SAMP:COUN {count}')
        self.inst.write('INIT')

        return float(self.inst.query('CALC:AVER:AVER?'))

