This is still quite a bit of a works-in-progress, but it's getting closer to usable. 
The idea is that the HPMA115S0 sensor has a fairly short fan life of about 2 years.
But if you shut the fan off between readings, you can likely extend it to at least 7 years.
This also benefits by reducing power consumption between readings as the fan is power-hungry.

Currently, the Pycom seems to cause the HPMA sensor to get hung up in a locked state and unable to respond to input.
I've seen two different conditions. One is that it's stuck auto-transmitting and won't ack/nack any received commands.
The other is that it accepted the stop reading command (Fan shuts off) and Stop Auto TX command but no longer accepts commands.
In both cases, the only fix so far is to power the sensor off for 5 seconds, then reboot the Pycom
