#ifndef GARDEN_API_H
#define GARDEN_API_H

#include <Arduino.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>


class GardenAPI {

private:

    String server;
    String apiKey;
    String bedID;


public:

    GardenAPI(
        String serverURL,
        String key,
        String id
    )
    {
        server = serverURL;
        apiKey = key;
        bedID = id;
    }



    bool sendSensorData(
        int average,
        int sensors[],
        int count,
        int rssi,
        String valve
    );


    bool shouldWater(
        int moisture
    );


    bool heartbeat(
        String ip,
        int rssi
    );


    bool getConfig(
        int &threshold,
        int &duration
    );

};


#endif