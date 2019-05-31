# PiGPIO Adapter

Provides an interface with a Raspberry Pi's GPIO ports using pigpio.

## Installation

You can find an installation guide on the [official website](http://abyz.me.uk/rpi/pigpio/download.html).

On Raspbian you only need to run

    sudo apt update
    sudo apt install pigpio

The simplest way to automatically run pigpio on boot would be:

    sudo bash -c "echo /usr/bin/pigpiod >> /etc/rc.local"
