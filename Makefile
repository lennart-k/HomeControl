pylint:
	pylint homecontrol --rcfile=pylintrc

venv:
	python3 -m venv ./venv --clear
	./venv/bin/python3 setup.py develop

tag:
	git tag v`python3 -c "from homecontrol.const import VERSION_STRING; print(VERSION_STRING)"`
