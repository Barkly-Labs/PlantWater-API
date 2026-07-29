
from machine import ADC, Pin
import time


class SoilSensor:


    def __init__(
        self,
        pin,
        dry_value=3000,
        wet_value=1200,
        samples=10
    ):

        self.pin = pin

        self.dry_value = dry_value
        self.wet_value = wet_value

        self.samples = samples


        self.adc = ADC(
            Pin(pin)
        )


        # ESP32 ADC range
        self.adc.atten(
            ADC.ATTN_11DB
        )


        self.filtered = 0





    def read_raw(self):

        """
        Read raw ADC value

        ESP32:
        0 - 4095
        """


        total = 0


        for i in range(
            self.samples
        ):

            total += self.adc.read()

            time.sleep_ms(5)



        return total // self.samples






    def read_percent(self):

        """
        Convert ADC reading
        into soil moisture %

        0% = dry
        100% = wet
        """


        raw = self.read_raw()



        percent = (

            (self.dry_value - raw)

            /

            (self.dry_value - self.wet_value)

        ) * 100



        percent = max(
            0,
            min(
                100,
                percent
            )
        )



        # Low-pass filter
        self.filtered = (

            self.filtered * 0.8

            +

            percent * 0.2

        )



        return round(
            self.filtered,
            1
        )






    def is_dry(
        self,
        threshold=30
    ):

        """
        Returns True if soil is dry
        """

        return (
            self.read_percent()
            <
            threshold
        )







    def calibrate(
        self,
        dry,
        wet
    ):

        """
        Change calibration values

        Example:

        dry = sensor in dry soil
        wet = sensor in wet soil
        """


        self.dry_value = dry

        self.wet_value = wet







    def get_status(self):

        """
        Return full sensor data
        """

        return {

            "pin": self.pin,

            "raw":
                self.read_raw(),

            "moisture":
                self.read_percent()

        }