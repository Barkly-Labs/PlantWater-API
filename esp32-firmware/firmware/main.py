from soil_sensor import SoilSensor
from garden_api import GardenAPI
from valve import Valve


def main():

    connect_wifi()

    setup_sensors()

    while True:

        read soil

        send data

        check watering

        control valve

        sleep


main()