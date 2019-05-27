pylint:
	pylint homecontrol homecontrol/modules homecontrol/dependencies --rcfile=pylintrc

flake8:
	flake8

docker:
	docker build .