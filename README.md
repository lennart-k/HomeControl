[![](https://readthedocs.org/projects/homecontrol/badge/?version=latest&style=flat)](https://homecontrol.readthedocs.io/en/latest/)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/lennart-k/HomeControl.svg?logo=lgtm&logoWidth=18&style=flat)](https://lgtm.com/projects/g/lennart-k/HomeControl/alerts/)
[![CodeFactor](https://www.codefactor.io/repository/github/lennart-k/homecontrol/badge)](https://www.codefactor.io/repository/github/lennart-k/homecontrol)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/lennart-k/HomeControl.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/lennart-k/HomeControl/context:python)
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
git clone https://github.com/lennart-k/HomeControl
cd HomeControl

pip install -r requirements.txt

python homecontrol --help
```

```
usage: homecontrol [-h] [-cfgfile CFGFILE] [-pid-file PID_FILE] [-clearport]
                   [-verbose] [-daemon]

HomeControl

optional arguments:
  -h, --help            show this help message and exit
  -cfgfile CFGFILE, -cf CFGFILE
                        File storing the HomeControl configuration
  -pid-file PID_FILE    Location of the PID file when running as a daemon.
                        Ensures that only one session is running
  -clearport            Frees the port for the API server using fuser.
                        Therefore only available on Linux
  -verbose
  -daemon, -d           Start HomeControl as a daemon process
  ```


## Features

- [x] Automation
- [x] Szenes
- [x] API
  - [x] Webhooks 
- [x] API v2
  - [ ] web interface (in progress)
- [ ] Tests
- [x] Docker builds
  - [ ] Automated ARM builds
- [ ] Data validation
  - [x] item config  
  - [x] item states
  - [ ] configuration.yaml


## Compatible Modules

- Chromecast
  - 433MHz switches
- IR devices
- MQTT
- Raspberry Pi (GPIO)
- RF devices
