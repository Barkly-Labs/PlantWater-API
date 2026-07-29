#ifndef VALVE_CONTROLLER_H
#define VALVE_CONTROLLER_H

#include <Arduino.h>


class ValveController {


private:

    uint8_t pin;


public:


    ValveController(
        uint8_t relayPin
    )
    {
        pin = relayPin;
    }



    void begin()
    {
        pinMode(
            pin,
            OUTPUT
        );

        off();
    }



    void on()
    {
        digitalWrite(
            pin,
            HIGH
        );
    }



    void off()
    {
        digitalWrite(
            pin,
            LOW
        );
    }


};



#endif