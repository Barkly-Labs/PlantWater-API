#include "WiFiManager.h"



bool WiFiManager::connect()
{

    Serial.println(
        "Connecting WiFi..."
    );


    WiFi.begin(
        ssid.c_str(),
        password.c_str()
    );


    int attempts = 0;


    while(
        WiFi.status() != WL_CONNECTED
        &&
        attempts < 30
    )
    {

        delay(500);

        Serial.print(".");

        attempts++;

    }



    if(
        WiFi.status()
        ==
        WL_CONNECTED
    )
    {

        Serial.println();

        Serial.println(
            "WiFi Connected!"
        );


        Serial.println(
            WiFi.localIP()
        );


        return true;

    }



    Serial.println(
        "WiFi Failed"
    );


    return false;

}





bool WiFiManager::connected()
{

    return WiFi.status()
        ==
        WL_CONNECTED;

}





String WiFiManager::ip()
{

    return WiFi.localIP()
        .toString();

}