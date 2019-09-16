[![](https://readthedocs.org/projects/homecontrol/badge/?version=latest&style=flat)](https://homecontrol.readthedocs.io/en/latest/)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/lennart-k/HomeControl.svg?logo=lgtm&logoWidth=18&style=flat)](https://lgtm.com/projects/g/lennart-k/HomeControl/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/lennart-k/HomeControl.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/lennart-k/HomeControl/context:python)
[![CodeFactor](https://www.codefactor.io/repository/github/lennart-k/homecontrol/badge)](https://www.codefactor.io/repository/github/lennart-k/homecontrol)
[![Docker status](https://img.shields.io/docker/cloud/build/lennartk01/homecontrol.svg)](https://hub.docker.com/r/lennartk01/homecontrol)
# HomeControl

Another approach to home automation

---

## Installation

### Docker

On amd64/x86 do:
```
docker run -it --net=host -v CONFIG_FOLDER:/config --name="HomeControl" lennartk01/homecontrol:latest
```

On arm machines like the Raspberry Pi do:
```
docker run -it --net=host -v CONFIG_FOLDER:/config --name="HomeControl" lennartk01/homecontrol:arm
```
If you are using arm you should consider the manual installation as I've not been able to set up automated builds for arm.


### Python

The minimum Python version for HomeControl is Python 3.6
You can install it the following:
```
python -m pip install git+https://github.com/lennart-k/HomeControl

homecontrol
```

#### Note

- Ensure that `python` refers to Python 3 and not Python 2
- Run homecontrol as `root` or install it with the `-U` parameter for HomeControl to install pip modules automatically


If you want to participate in developing HomeControl consider following techniques:
```
git clone https://github.com/lennart-k/HomeControl
cd HomeControl


python setup.py develop
homecontrol --help

OR

pip install -r requirements.txt
python -m homecontrol --help
```

```
usage: homecontrol [-h] [-cfgdir CFGDIR] [-pid-file PID_FILE] [-clearport]
                   [-verbose] [-nocolor] [-logfile LOGFILE] [-killprev]
                   [-skip-pip] [-daemon]

HomeControl

optional arguments:
  -h, --help            show this help message and exit
  -cfgdir CFGDIR, -cd CFGDIR
                        Directory storing the HomeControl configuration
  -pid-file PID_FILE    Location of the PID file.Ensures that only one session
                        is running.Defaults to the configuration path
  -clearport            Frees the port for the API server using
                        fuser.Therefore only available on Linux
  -verbose              Sets the loglevel for the logfile to INFO
  -nocolor              Disables colored console output
  -logfile LOGFILE      Logfile location
  -killprev, -kp        Kills the previous HomeControl instance
  -skip-pip, -sp        Skips the installation of configured pip requirements
  -daemon, -d           Start HomeControl as a daemon process [posix only]

  ```

## Documentation

Documentation is currently in the works.
You can find it [here](https://homecontrol.readthedocs.io/en/latest/).


## Features

- Automation
- Szenes
- API
  - WebHooks
  - WebSockets
  - SSL
- Docker builds

[Homecontrol v1.0.0 Project board](https://github.com/lennart-k/HomeControl/projects/3)

## Compatible Devices/Protocols

- Chromecast
- 433MHz switches
- IR devices
- MQTT
- Raspberry Pi (GPIO)
  - MCP3008 ADC
  - 433MHz adapter
  - RGB Lights
- RF devices
- Yamaha AV receivers
- Pushbullet (Send message)
- Speedtest
