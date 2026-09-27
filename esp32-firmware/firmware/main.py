import time
import machine

from pid import PIDController
from soil_sensor import SoilSensor
from valve import Valve
from wifi_manager import WiFiManager
from garden_api import GardenAPI



# ==========================
# CONFIGURATION
# ==========================

BED_ID = "bed_1"

SERVER_URL = "http://192.168.1.100:8000"

API_KEY = "YOUR_API_KEY"


TARGET_MOISTURE = 520


PID_CONFIG = {
    "kp": 0.18,
    "ki": 0.001,
    "kd": 0.04
}


MAX_WATER_TIME = 8

COOLDOWN = 600   # seconds



# ==========================
# HARDWARE SETUP
# ==========================

print("🌱 Starting Garden Node")



soil = SoilSensor(
    pins=[
        34,
        35,
        32,
        33,
        39
    ]
)


valve = Valve(
    pin=26
)



# ==========================
# CONTROLLERS
# ==========================

pid = PIDController(

    kp=PID_CONFIG["kp"],
    ki=PID_CONFIG["ki"],
    kd=PID_CONFIG["kd"],

    target=TARGET_MOISTURE

)



# ==========================
# NETWORK
# ==========================

wifi = WiFiManager()

wifi.connect()



api = GardenAPI(

    server_url=SERVER_URL,
    api_key=API_KEY,
    bed_id=BED_ID

)



# ==========================
# STATE
# ==========================

last_water_time = 0

boot_time = time.time()



# ==========================
# SAFETY
# ==========================

def emergency_shutdown():

    print(
        "⚠️ Emergency valve shutdown"
    )

    valve.off()



# Ensure valve is OFF after reset
valve.off()



# ==========================
# WATERING CONTROL
# ==========================

def run_watering(seconds):

    global last_water_time


    seconds = min(
        seconds,
        MAX_WATER_TIME
    )


    print(
        "💧 Watering:",
        seconds,
        "seconds"
    )


    valve.on()



    start = time.time()


    while (
        time.time()
        -
        start
        <
        seconds
    ):

        # Keep system alive
        time.sleep(0.1)



    valve.off()



    last_water_time = time.time()



# ==========================
# MAIN LOOP
# ==========================

def main():

    global last_water_time


    print(
        "✅ Garden node online"
    )



    while True:


        try:


            # ----------------------
            # READ SENSORS
            # ----------------------

            average, readings = (
                soil.read()
            )


            print(
                "Sensors:",
                readings
            )


            print(
                "Average:",
                average
            )



            # ----------------------
            # PID DECISION
            # ----------------------

            water_time = (
                pid.compute(
                    average
                )
            )



            # ----------------------
            # SAFETY CHECK
            # ----------------------

            cooldown_done = (
                time.time()
                -
                last_water_time
                >
                COOLDOWN
            )



            if (
                water_time > 0
                and
                cooldown_done
            ):

                run_watering(
                    water_time
                )



            else:

                print(
                    "No watering needed"
                )



            # ----------------------
            # SEND DATA
            # ----------------------

            api.send_data(

                sensors=readings,

                average=average,

                valve_state=(
                    valve.state()
                )

            )



            # ----------------------
            # HEARTBEAT
            # ----------------------

            api.heartbeat()



        except Exception as e:


            print(
                "ERROR:",
                e
            )


            emergency_shutdown()



        # Sensor update interval

        time.sleep(30)




# ==========================
# START
# ==========================

if __name__ == "__main__":

    main()