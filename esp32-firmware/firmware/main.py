from soil_sensor import SoilSensor
from garden_api import GardenAPI
from valve import Valve
from wifi_manager import WiFiManager
from soil_sensor import SoilSensor


def main():

    WiFiManager.connect()

    SoilSensor.init()

    while True:

        #read soil

        #send data

        #check watering

        #control valve

        #sleep


main()