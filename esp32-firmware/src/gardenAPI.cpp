#include "GardenAPI.h"



bool GardenAPI::sendSensorData(
    int average,
    int sensors[],
    int count,
    int rssi,
    String valve
){

    HTTPClient http;


    http.begin(
        server + "/api/bed-data"
    );


    http.addHeader(
        "Content-Type",
        "application/json"
    );


    http.addHeader(
        "X-API-Key",
        apiKey
    );


    StaticJsonDocument<512> doc;


    doc["bed_id"] = bedID;
    doc["average"] = average;
    doc["rssi"] = rssi;
    doc["valve_state"] = valve;


    JsonArray arr =
        doc.createNestedArray("sensors");


    for(int i=0;i<count;i++)
    {
        arr.add(sensors[i]);
    }


    String body;


    serializeJson(
        doc,
        body
    );


    int code =
        http.POST(body);


    http.end();


    return code == 200;

}






bool GardenAPI::shouldWater(
    int moisture
){

    HTTPClient http;


    String url =
    server +
    "/api/should-water?bed_id="
    + bedID +
    "&average_moisture="
    + moisture;


    http.begin(url);


    http.addHeader(
        "X-API-Key",
        apiKey
    );


    int code =
        http.POST("");



    if(code != 200)
    {
        http.end();
        return false;
    }


    String response =
        http.getString();


    http.end();



    StaticJsonDocument<256> doc;


    deserializeJson(
        doc,
        response
    );


    return doc["water"];

}






bool GardenAPI::heartbeat(
    String ip,
    int rssi
){

    HTTPClient http;


    String url =
    server +
    "/api/node/heartbeat?"
    "bed_id="
    + bedID +
    "&ip="
    + ip +
    "&rssi="
    + String(rssi);



    http.begin(url);


    int code =
        http.POST("");



    http.end();


    return code == 200;

}





bool GardenAPI::getConfig(
    int &threshold,
    int &duration
){

    HTTPClient http;


    http.begin(
        server +
        "/api/config/" +
        bedID
    );


    int code =
        http.GET();


    if(code != 200)
    {
        http.end();
        return false;
    }


    String data =
        http.getString();


    http.end();



    StaticJsonDocument<256> doc;


    deserializeJson(
        doc,
        data
    );


    threshold =
        doc["moisture_threshold"];


    duration =
        doc["watering_duration_sec"];



    return true;

}