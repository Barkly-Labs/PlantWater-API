from machine import Pin
import time


class ValveController:


    def __init__(
        self,
        pin,
        active_high=True
    ):

        self.pin_number = pin

        self.active_high = active_high


        self.pin = Pin(
            pin,
            Pin.OUT
        )


        self.state = False


        self.off()



    def on(self):

        """
        Turn valve ON
        """

        if self.active_high:

            self.pin.value(1)

        else:

            self.pin.value(0)


        self.state = True



    def off(self):

        """
        Turn valve OFF
        """

        if self.active_high:

            self.pin.value(0)

        else:

            self.pin.value(1)


        self.state = False




    def toggle(self):

        """
        Flip valve state
        """

        if self.state:

            self.off()

        else:

            self.on()





    def is_on(self):

        return self.state





    def water_for(
        self,
        seconds
    ):

        """
        Run irrigation
        for a set time
        """

        self.on()


        time.sleep(
            seconds
        )


        self.off()