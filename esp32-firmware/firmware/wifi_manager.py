import network
import time


class WiFiManager:


    def __init__(
        self,
        ssid,
        password
    ):

        self.ssid = ssid
        self.password = password

        self.wlan = network.WLAN(
            network.STA_IF
        )



    def connect(
        self,
        timeout=30
    ):

        """
        Connect ESP32 to WiFi
        """

        print(
            "Starting WiFi..."
        )


        self.wlan.active(True)


        if self.wlan.isconnected():

            print(
                "Already connected"
            )

            return True



        self.wlan.connect(
            self.ssid,
            self.password
        )


        start = time.time()


        while not self.wlan.isconnected():


            if time.time() - start > timeout:

                print(
                    "WiFi timeout"
                )

                return False



            print(
                ".",
                end=""
            )


            time.sleep(1)



        print()

        print(
            "WiFi connected!"
        )


        print(
            "IP:",
            self.ip()
        )


        return True





    def disconnect(self):

        """
        Disconnect WiFi
        """

        self.wlan.disconnect()





    def connected(self):

        """
        Check WiFi status
        """

        return self.wlan.isconnected()





    def reconnect(self):

        """
        Restore connection
        """

        if not self.connected():

            print(
                "Reconnecting WiFi..."
            )

            return self.connect()


        return True





    def ip(self):

        """
        Get ESP32 IP
        """

        if self.connected():

            return self.wlan.ifconfig()[0]


        return None





    def rssi(self):

        """
        Get signal strength
        """

        if self.connected():

            return self.wlan.status(
                "rssi"
            )


        return -100





    def info(self):

        """
        Return WiFi information
        """

        return {

            "connected":
                self.connected(),

            "ip":
                self.ip(),

            "rssi":
                self.rssi()

        }