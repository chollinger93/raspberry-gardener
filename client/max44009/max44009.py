from smbus2 import SMBus
import time

class MAX44009:
    # Thanks to https://github.com/rcolistete/MicroPython_MAX44009_driver/blob/master/max44009.py
    # With slight adjustments by chollinger93 for Python3 etc.
    MAX44009_I2C_DEFAULT_ADDRESS = 0x4A
    MAX44009_I2C_FALLBACK_ADDRESS = 0x4B

    MAX44009_REG_CONFIGURATION = 0x02
    MAX44009_REG_LUX_HIGH_BYTE = 0x03
    MAX44009_REG_LUX_LOW_BYTE  = 0x04
    
    MAX44009_REG_CONFIG_CONTMODE_DEFAULT     = 0x00    # Default mode, low power, measures only once every 800ms regardless of integration time
    MAX44009_REG_CONFIG_CONTMODE_CONTINUOUS  = 0x80    # Continuous mode, readings are taken every integration time
    MAX44009_REG_CONFIG_MANUAL_OFF           = 0x00    # Automatic mode with CDR and Integration Time are are automatically determined by autoranging
    MAX44009_REG_CONFIG_MANUAL_ON            = 0x40    # Manual mode and range with CDR and Integration Time programmed by the user
    MAX44009_REG_CONFIG_CDR_NODIVIDED        = 0x00    # CDR (Current Division Ratio) not divided, all of the photodiode current goes to the ADC
    MAX44009_REG_CONFIG_CDR_DIVIDED          = 0x08    # CDR (Current Division Ratio) divided by 8, used in high-brightness situations
    MAX44009_REG_CONFIG_INTRTIMER_800        = 0x00    # Integration Time = 800ms, preferred mode for boosting low-light sensitivity
    MAX44009_REG_CONFIG_INTRTIMER_400        = 0x01    # Integration Time = 400ms
    MAX44009_REG_CONFIG_INTRTIMER_200        = 0x02    # Integration Time = 200ms
    MAX44009_REG_CONFIG_INTRTIMER_100        = 0x03    # Integration Time = 100ms, preferred mode for high-brightness applications
    MAX44009_REG_CONFIG_INTRTIMER_50         = 0x04    # Integration Time = 50ms, manual mode only
    MAX44009_REG_CONFIG_INTRTIMER_25         = 0x05    # Integration Time = 25ms, manual mode only
    MAX44009_REG_CONFIG_INTRTIMER_12_5       = 0x06    # Integration Time = 12.5ms, manual mode only
    MAX44009_REG_CONFIG_INTRTIMER_6_25       = 0x07    # Integration Time = 6.25ms, manual mode only

    def __init__(self, bus=None) -> None:
        if not bus:
            bus = SMBus(1)
        self.bus = bus
        self.addr = self.MAX44009_I2C_DEFAULT_ADDRESS
        self.configure()

    def configure(self):
        try:
            self.bus.write_byte_data(self.addr, 
                self.MAX44009_REG_CONFIGURATION, 
                self.MAX44009_REG_CONFIG_MANUAL_ON)
        except Exception as e:
            print(e)

    def _convert_lumen(self, raw) -> float:
        exponent = (raw[0] & 0xF0) >> 4
        mantissa = ((raw[0] & 0x0F) << 4) | (raw[1] & 0x0F)
        return ((2 ** exponent) * mantissa) * 0.045

    def read_lumen(self)-> float:
        data = self.bus.read_i2c_block_data(self.addr,
            self.MAX44009_REG_LUX_HIGH_BYTE, 2)
        return self._convert_lumen(data)
    
    def _switch_addr(self):
        if self.addr == self.MAX44009_I2C_DEFAULT_ADDRESS:
            self.addr = self.MAX44009_I2C_FALLBACK_ADDRESS
        else:
            self.addr = self.MAX44009_I2C_DEFAULT_ADDRESS

    def read_lumen_with_retry(self):
        # To avoid 121 I/O error
        # Sometimes, the sensor listens on 0x4A,
        # sometimes, on 0x4B (ಠ.ಠ)
        try:
            return self.read_lumen()
        except Exception as e:
            print(f'Error reading lumen on {self.addr}, retrying')
            self._switch_addr()
            self.configure()
            return self.read_lumen_with_retry()

if __name__ == '__main__':
    # Get I2C bus
    bus = SMBus(1)
    # Let I2C settle
    time.sleep(0.5)
    MAX44009 = MAX44009(bus)
    # Convert the data to lux
    luminance = MAX44009.read_lumen_with_retry()

    # Output data to screen
    print(f'Ambient Light luminance : {luminance} lux')