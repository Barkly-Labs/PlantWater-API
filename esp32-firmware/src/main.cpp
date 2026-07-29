#include "WiFiManager.h"
#include "SoilSensor.h"
#include "GardenAPI.h"
#include "ValveController.h"



//
// WIFI
//

WiFiManager wifi(
    "YOUR_WIFI_NAME",
    "YOUR_WIFI_PASSWORD"
);




// SERVER

GardenAPI api(
    "http://192.168.1.100:8000",
    "YOUR_API_KEY",
    "garden_1"
);




// SOIL SENSORS

SoilSensor sensors[] =
{

    SoilSensor(34),
    SoilSensor(35),
    SoilSensor(32),
    SoilSensor(33),
    SoilSensor(36)

};




// VALVE

ValveController valve(
    25
);




void setup()
{

    Serial.begin(115200);



    wifi.connect();



    for(
        auto &sensor : sensors
    )
    {
        sensor.begin();
    }



    valve.begin();


}





void loop()
{


    int raw[5];

    int total = 0;



    for(
        int i=0;
        i<5;
        i++
    )
    {

        raw[i] =
            sensors[i]
            .getRaw();


        total += raw[i];

    }




    int average =
        total / 5;



    Serial.print(
        "Soil:"
    );

    Serial.println(
        average
    );





    //
    // SEND DATA TO SERVER
    //

    api.sendSensorData(
        average,
        raw,
        5,
        WiFi.RSSI(),
        "OFF"
    );





    //
    // ASK SERVER
    //

    bool water =
        api.shouldWater(
            average
        );



    if(water)
    {

        Serial.println(
            "Watering"
        );


        valve.on();


        delay(
            30000
        );


        valve.off();

    }





    delay(
        60000
    );

}