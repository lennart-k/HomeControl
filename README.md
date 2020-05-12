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

### Python

The minimum Python version for HomeControl is Python 3.7
You can install it the following:
```
python3 -m pip install git+https://github.com/lennart-k/HomeControl
```

#### Note

- Run homecontrol as `root` or install it with the `-U` parameter for HomeControl to install pip modules automatically

