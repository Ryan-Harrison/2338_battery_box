Introduction
============

This code was written in Python3 by Ryan Harrison for FRC Team 2338 Gear 
It Forward. The purpose of this code is to operate a series of chargers 
to charge three banks simultaneously and autonomously migrate from the 
top battery to the bottom. The code was written for use on a Raspberry Pi 
Model B Rev 2 and interfaces with a Denkovi USB 16 Channel Relay Module - RS232 Controlled, 
12V - ver.2. Information on this relay module can be 
found at denkovi.com/usb-16-channel-relay-module-rs232-controlled-12v-ver.2 
(Insert link and info about the charger here)

Adapting
========

Adapting this code for your use will likely require some changes. Gear 
It Forward employs the use of photoreceptors plugged into the GPIO ports 
in the Raspberry Pi. These ports are probed for their values at regular 
intervals. If you also use photoreceptors in your batterybox, you will 
need to take note of the ports that you have plugged them into and 
change them accordingly where they appear in the code. If you employ 
another strategy for checking on the charging state of your batteries, 
I would suggest only using this code as a starting point, as a large 
portion of it revolves around checking on the LEDs from the charger.
