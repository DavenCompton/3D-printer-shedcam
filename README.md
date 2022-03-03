# 3D-shedcam

This package provides USB webcam and DS18B20 temperature sensor remote monitoring for an outside shed-based 3D printing setup. As the outside shed provides greater space for equipment and workflow, and keeps chemicals out of the house, it is the preferable location to house a 3D printing setup. The downside is that monitoring the 3D printer is inconvenient. This package allows the real-time monitoring of operating temperatures and visual progress of prints using a flask webserver on a Raspberry Pi 3B+ serving up temperature readings from a DS18B20 temperature sensor and video from a generic USB webcam.


## Hardware requirements

### Raspberry Pi 3B+

This works on the Raspberry Pi 4B 8GB as well, but since I have several 3B+'s lying around, it was decided to use a 3B+ in a permanent role.

### Ethernet cable

The shed has network points throughout, so the Raspberry Pi 3B+ was not configured to make use of Wi-Fi connectivity.

### DS18B20 temperature sensor

An Arduino Digital Temperature Sensor Module using the OneWire protocol from [Jaycar](https://www.jaycar.com.au/digital-temperature-sensor-module/p/XC3700) (Cat.No. XC3700) was used. This module uses the '-' pin for GND, the '+' middle pin to 5V and the 'S' pin to a digital pin.

### Webcam

A Logitech 920 webcam and an unknown Sony webcam found in the bottom of a drawer were both used successfully. An inexpensive webcam will provide more than enough resolution to observe the print progress. Any generic webcam should suffice.

### 150mm Socket to Socket Jumper Leads

Socket to Socket Juper Leads from [Jaycar](https://www.jaycar.com.au/150mm-socket-to-socket-jumper-leads-40-piece/p/WC6026) (Cat.No. WC6026) were used to connect the DS18B20 Temperature Sensor to the Raspberry Pi 3B+'s GPIO pins.


## Software used

### Flask

Provides the webserver

### OpenCV

Used to obtain the video from the webcam and superimpose data on the video stream.


## Preparing the Raspberry Pi 3B+

As of this commit, Raspbian OS was still on Buster (Debian Release 10) [2021-05-07-raspios-buster-armhf-lite.zip](https://www.raspberrypi.org/software/operating-systems/) even though Debian stable had moved on to [Bullseye (Debian Release 11)](https://raspi.debian.net/tested-images/). This preparation is based on Buster-based Raspbian OS.

### Make the Raspberry Pi 3B+ headless

The latest Raspbian OS lite/headless version was downloaded from the official Rasberry Pi [sources](https://www.raspberrypi.org/software/operating-systems/), checked using the provided SHA256 hash, extracted and then flashed onto a SD card using [balenaEtcher](https://www.balena.io/etcher/). After removing the SD card from the Windows workstation, it is reinserted. A warning is shown by Windows Explorer which can be ignored and closed. In Windows Explorer, a new 'boot' partition will be available. Open this partition and create a new empty file called 'ssh' (right click > New > Text Document) removing the '.txt' extension. This enables the SSH server on the Raspberry Pi on first boot so one can login remotely - the Raspberry Pi is now headless. Insert the SD card into the Raspberry Pi and start it. Find the IP address of the Raspberry Pi and login over SSH using the default user 'pi' and the default password 'raspberry'. Change the password...

### Configure Raspbian OS using raspi-config

Personal preference is to operate as the root user when making system changes.

    sudo su -
  
The Raspberry Pi 3B+ was configured using

    raspi-config

The following were configured in raspi-config:
* System Options > Hostname > 'shed-pi3'
* Localisation Options > Locale > 'en_AU.UTF-8 UTF-8' > Select 'en_AU.UTF-8 UTF-8' as default locale for the system environment
* Localisation Options > Timezone > As appropriate...

After a reboot, the systems' localisation is configured appropriately.

### Update Raspbian OS

One can update the system with

    apt update && apt upgrade -y

There was an error regarding the downloading of packages from the main Raspbian OS mirror used [Down Under](http://mirror.aarnet.edu.au). It is unknown if the error is transient, but the following changes to the 'apt' system resulted in success

    sed -i 's|deb http://raspbian.raspberrypi.org/raspbian/ buster main contrib non-free rpi|#deb http://raspbian.raspberrypi.org/raspbian/ buster main contrib non-free rpi|' /etc/apt/sources.list
    echo 'deb http://mirror.aarnet.edu.au/pub/raspbian/raspbian/ buster main contrib non-free rpi' >> /etc/apt/sources.list
    apt update && apt upgrade -y

The following packages are generally needed for convenience and development with VS Code

    apt install -y curl wget tmux python3-venv python3-pip git

The following packages are required for the proper functioning of OpenCV

    apt install -y libjpeg-dev libtiff-dev libjasper-dev libpng-dev libwebp-dev libopenexr-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libdc1394-22-dev libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev libatlas-base-dev liblapacke-dev gfortran libhdf5-dev libhdf5-103


## Python development for the webcam

As the 'pi' user, a working directory is created

    mkdir ~/webcam

A python3 virtual environment is created within this directory with an alias to conveniently activate the python virtual environment

    cd webcam
    python3 -m venv .venv
    echo "alias activate-webcam='source ~/webcam/.venv/bin/activate && cd ~/webcam'" >> ~/.bash_aliases
    source ~/.bashrc

Activate the python virtual environment and install the required packages using 'pip'

    activate-webcam
    pip install flask flask-socketio eventlet opencv-python-headless RPi.GPIO w1thermsensor

Once the python packages are installed, clone this repository

    git clone https://github.com/DavenCompton/3D-printer-shedcam.git .

The script is run with

    python3 monitor.py 8080

Using an internet browser, navigate to the approporate IP address and port of the Raspberry Pi 3B+. The video stream should be available to view.

## Configuring the DS18B20 Temerature Sensor

The default pin for 1-wire comms is GPIO 4. The GPIO pins do not map directly to the physical pins, as stated in the official [GPIO and the 40-pin Header](https://www.raspberrypi.org/documentation/computers/os.html#gpio-and-the-40-pin-header) documentation. So for the DS18B20 Digital Temperature Sensor Module, the following connections are to be made:

* Physical Pin 2 (5V)       -> '+' centre leg
* Physical Pin 6 (GND)      -> '-' left leg
* Physical Pin 7 (GPIO 4)   -> 'S' right leg

To dynamically load the overlay and test the sensor

    dtoverlay w1-gpio gpiopin=4
    
then discover the sensor by listing the contents of the */sys/bus/drivers* directory. The sensor is identified by the directory starting with a number. Displaying the contents of the *w1_slave* file inside the sensor's directory shows the temperature on the second line.

    cat /sys/bus/w1/devices/28-011441bdcfaa/w1_slave
    
    44 01 4b 46 7f ff 0c 10 a9 : crc=a9 YES
    44 01 4b 46 7f ff 0c 10 a9 t=20250
    
The temperature measured is 20.250C.

To permanently enable the 1-wire interface, use the *raspi-config* utility

* Interface Options > P7 1-Wire      Enable/disable one-wire interface > Yes

To enable non-default GPIO pins for 1-wire, then add the following line to */boot/config.txt* as described [here](https://pinout.xyz/pinout/1_wire#)

    dtoverlay=w1-gpio,gpiopin=x
 
 where *x* is the GPIO pin you want to use (Note this is not the physical header pin - a [mapping](https://www.raspberrypi.org/documentation/computers/os.html#gpio-and-the-40-pin-header) must be made).
 
 To dynamically enable the GPIO pin, use
 
     dtoverlay w1-gpio gpiopin=x
