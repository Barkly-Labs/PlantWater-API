#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>


class WiFiManager {

private:

    String ssid;
    String password;


public:

    WiFiManager(
        String wifiSSID,
        String wifiPassword
    )
    {
        ssid = wifiSSID;
        password = wifiPassword;
    }



    bool connect();

    bool connected();

    String ip();

};



#endif