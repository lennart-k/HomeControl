# HomeControl
[![](https://readthedocs.org/projects/homecontrol/badge/?version=latest&style=flat)](https://homecontrol.readthedocs.io/en/latest/)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/lennart-k/HomeControl.svg?logo=lgtm&logoWidth=18&style=flat)](https://lgtm.com/projects/g/lennart-k/HomeControl/alerts/)

--- 


# Installation


## Docker

docker run -it --net=host -v CONFIG_FOLDER:/config --name="HomeControl" lennartk01/homecontrol:latest


## Python

The minimum Python version for HomeControl is Python 3.6
You can install it the following:
```bash
git clone https://github.com/lennart-k/HomeControl
cd HomeControl

pip install -r requirements.txt

python homecontrol --help
```

