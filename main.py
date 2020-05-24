
import nets
import machine
import socket
import ubinascii
import struct
import time
import os
import math
import pycom
import ustruct

from machine import UART
pycom.heartbeat(False) #needs to be disabled for LED functions to work
pycom.rgbled(0x7f0000) #red
read_timeout=2000
#get online using known nets if available
if machine.reset_cause() != machine.SOFT_RESET:
    from network import WLAN
    wl = WLAN()
    wl.mode(WLAN.STA)
    original_ssid = wl.ssid()
    original_auth = wl.auth()

    print("Scanning for known wifi nets")
    available_nets = wl.scan()
    netsisee = frozenset([e.ssid for e in available_nets])

    known_nets_names = frozenset([key for key in nets.known_nets])
    net_to_use = list(netsisee & known_nets_names)
    try:
        net_to_use = net_to_use[0]
        net_properties = nets.known_nets[net_to_use]
        pwd = net_properties['pwd']
        sec = [e.sec for e in available_nets if e.ssid == net_to_use][0]
        if 'wlan_config' in net_properties:
            wl.ifconfig(config=net_properties['wlan_config'])
        wl.connect(net_to_use, (sec, pwd), timeout=10000)
        while not wl.isconnected():
            machine.idle() # save power while waiting
        print("Connected to "+net_to_use+" with IP address:" + wl.ifconfig()[0])
        pybytes.reconnect()

    except Exception as e:
        print("Failed to connect to any known network, going into AP mode")
        wl.init(mode=WLAN.AP, ssid=original_ssid, auth=original_auth, channel=6, antenna=WLAN.INT_ANT)


import time,utime

try:
    uart = UART(1,9600)
    uart.init(9600,bits=8, parity=None, stop=1)
except NameError as exp: 
    print("error opening UART")
    raise UartException(str(exp))
#these are for the standard 32 byte packets
MSG_CHAR_1 = b'\x42' # First character to be recieved in a valid packet
MSG_CHAR_2 = b'\x4d' # Second character to be recieved in a valid packet

SHORT_MSG_CHAR_1=b'\x40'
SHORT_MSG_CHAR_2=b'\x05'
uart.init(timeout_chars=400)
data=b'xx'
while data is not None:
    data = uart.read(1)#flush the uart data
    #print(data)  #uncomment this to test whether you're getting data from the sensor in the first place
uart.init(timeout_chars=1000)



print("Starting")
#data= uart.readall()  #somehow readall seems deprecated?
time.sleep(1)# then give it another second for the next good byte to come in.
HPMAstart=[0x68,0x01, 0x01, 0x96]
HPMAstop=[0x68,0x01, 0x02, 0x95]
HPMAread=[0x68,0x01, 0x04, 0x93]
HPMAstopauto=[0x68,0x01, 0x20, 0x77]
HPMAstartauto=[0x68,0x01, 0x40, 0x57]
pm10=-1
pm25=-1
print("turning off fan briefly")
retries=4
dump=uart.read()
while(retries>0):
    print(dump)
    uart.write(bytearray(HPMAstopauto)) #Send command to stop auto send
    while not uart.wait_tx_done(100):
        machine.idle()
    dump=uart.read()
    if(dump is not None):
        if(dump[-2]==0xa5):
            if(dump[-1]==0xa5):
                print("ACK!")
                break
            else:
                print("NACK!")
                print(dump)
        else:
            print("NACK!")
            print(dump)
        retries-=1
    retries-=1
retries=4
while(retries>0):
    print(dump)
    uart.write(bytearray(HPMAstop)) #Send command to stop measurement
    while not uart.wait_tx_done(100):
        machine.idle()
    dump=uart.read()
    if(dump is not None):
        if(dump[-2]==0xa5):
            if(dump[-1]==0xa5):
                print("ACK!")
                break
            else:
                print("NACK!")
                print(dump)
        else:
            print("NACK!")
            print(dump)
        retries-=1
    retries-=1

print("Beginning loop")
while 1:
    print("Setting up HPMA")
    retries=3
    while(retries>0):
        print(dump)
        uart.write(bytearray(HPMAstop)) #Send command to start measurement
        while not uart.wait_tx_done(100):
            machine.idle()
        dump=uart.read()
        if(dump is not None):
            if(dump[-2]==0xa5):
                if(dump[-1]==0xa5):
                    print("ACK!")
                    break
                else:
                    print("NACK!")
                    print(dump)
            else:
                print("NACK!")
                print(dump)
            retries-=1
        retries-=1
    print("sleep 6s")
    time.sleep(6)#Give Honeywell sensor 6 seconds for readings to normalize
    print("get a reading")
    retries=3
    while(retries>0):
        print(dump)
        uart.write(bytearray(HPMAread)) #Send command to start measurement
        while not uart.wait_tx_done(100):
            machine.idle()
        start=utime.ticks_ms()
        recv=b''
        while(utime.ticks_diff(start,utime.ticks_ms())> -read_timeout):
            inp = uart.read(1) # Read a character from the input
            print(inp)
            if inp == SHORT_MSG_CHAR_1: # check it matches
            #print("got 1!")
                recv += inp # if it does add it to recieve string
                inp = uart.read(1) # read the next character
                if inp == SHORT_MSG_CHAR_2: # check it's what's expected
                    recv += inp # att it to the recieve string
                    recv += uart.read(6) # read the remaining 30 bytes
                    sent = 0
                    calc = 0
                    ord_arr=b''#None
                    ord_arr = []
                    for c in bytearray(recv[:-1]): #Add all the bytes together except the checksum bytes
                        calc += c
                        ord_arr.append(c)
                    sent = recv[-1] # Combine the 2 bytes together
                    if sent != calc:
                        print("Checksum failure %d != %d".format( sent , calc))
                    #print(recv)
                    else:
                        pm10 = int(recv[2]) * 256 + int(recv[3])
                        pm25 = int(recv[4]) * 256 + int(recv[5])
                        print("pm10 =%d" %pm10)
                        break
                else:
                    print("second char doesn't match %d" %inp)
                    


        retries-=1
                #return HoneywellReading(recv) # convert to reading object
            #If the character isn't what we are expecting loop until timeout
    #raise HoneywellException("No message received")
        if pm10>0:
            break
        print("ticks_diff=",utime.ticks_diff(start,utime.ticks_ms()))


    #s.setblocking(True)
    print("Sending data!")
    if pm25>0:
        print("pm2.5= {}, pm10= {}".format(pm25, pm10))
    else:
        print("No data received!")
    uart.write(bytearray(HPMAstop)) #Send command to start measurement
    while not uart.wait_tx_done(100):
        machine.idle()
#    uart.write(b'\x68\x01\x02\x95') #Send command to start measurement
#    while not uart.wait_tx_done(100):
 #       machine.idle()

    print("Sleeping 60s")
    time.sleep(60)#wait 5 minutes before next reading
