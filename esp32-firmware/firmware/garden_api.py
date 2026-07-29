import urequests
import json
import time


class GardenAPI:

    def __init__(
        self,
        server_url,
        api_key,
        bed_id
    ):

        self.server = server_url.rstrip("/")
        self.api_key = api_key
        self.bed_id = bed_id



    def _headers(self):

        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }



    def send_sensor_data(
        self,
        average,
        sensors,
        rssi,
        valve_state="OFF"
    ):

        """
        Send soil sensor readings
        to /api/bed-data
        """

        payload = {

            "bed_id": self.bed_id,

            "timestamp":
                self.timestamp(),

            "average": average,

            "sensors": sensors,

            "rssi": rssi,

            "valve_state": valve_state
        }


        try:

            response = urequests.post(

                self.server +
                "/api/bed-data",

                headers=self._headers(),

                data=json.dumps(payload)

            )


            result = response.json()

            response.close()


            return result



        except Exception as e:

            print(
                "API sensor error:",
                e
            )

            return None





    def should_water(
        self,
        moisture
    ):

        """
        Ask server if watering is needed
        """


        try:

            url = (
                self.server +
                "/api/should-water?"
                "bed_id="
                + self.bed_id +
                "&average_moisture="
                + str(moisture)
            )


            response = urequests.post(

                url,

                headers=self._headers()

            )


            data = response.json()

            response.close()


            return data



        except Exception as e:

            print(
                "Water check error:",
                e
            )

            return {
                "water": False
            }





    def heartbeat(
        self,
        ip,
        rssi
    ):

        """
        Tell server the ESP32 is alive
        """


        try:

            url = (
                self.server +
                "/api/node/heartbeat?"
                "bed_id="
                + self.bed_id +
                "&ip="
                + ip +
                "&rssi="
                + str(rssi)
            )


            response = urequests.post(
                url
            )


            data = response.json()

            response.close()


            return data



        except Exception as e:

            print(
                "Heartbeat error:",
                e
            )

            return None





    def get_config(self):

        """
        Download bed settings
        """


        try:

            response = urequests.get(

                self.server +
                "/api/config/" +
                self.bed_id

            )


            data = response.json()

            response.close()


            return data



        except Exception as e:

            print(
                "Config error:",
                e
            )

            return None





    def timestamp(self):

        """
        ESP32 timestamp placeholder.

        Later replace with NTP time.
        """

        t = time.localtime()


        return (
            "{}-{:02d}-{:02d}T"
            "{:02d}:{:02d}:{:02d}"
        ).format(

            t[0],
            t[1],
            t[2],
            t[3],
            t[4],
            t[5]

        )