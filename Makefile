pylint:
	pylint homecontrol homecontrol/modules homecontrol/dependencies --rcfile=pylintrc

flake8:
	flake8

docker:
	docker build .

tag:
	git tag v`python3 -c "from homecontrol.const import VERSION_STRING; print(VERSION_STRING)"`