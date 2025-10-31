.ONESHELL:
ENV_PREFIX=$(shell python -c "if __import__('pathlib').Path('.venv/bin/pip').exists(): print('.venv/bin/')")

.PHONY: help
help:             	## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: venv
venv:			## Create a virtual environment
	@echo "Creating virtualenv ..."
	@rm -rf .venv
	@python3 -m venv .venv
	@./.venv/bin/pip install -U pip
	@echo
	@echo "Run 'source .venv/bin/activate' to enable the environment"

.PHONY: install
install:		## Install dependencies
	pip install -r requirements-dev.txt
	pip install -r requirements-test.txt
	pip install -r requirements.txt

.PHONY: train
train:			## Train the model and save it to disk
	python -m challenge.train

STRESS_URL = https://flight-delay-api-n4pw2qn23q-uc.a.run.app
.PHONY: stress-test
stress-test:
	# change stress url to your deployed app 
	mkdir reports || true
	locust -f tests/stress/api_stress.py --print-stats --html reports/stress-test.html --run-time 60s --headless --users 100 --spawn-rate 1 -H $(STRESS_URL)

.PHONY: model-test
model-test:			## Run tests and coverage
	mkdir reports || true
	pytest --cov-config=.coveragerc --cov-report term --cov-report html:reports/html --cov-report xml:reports/coverage.xml --junitxml=reports/junit.xml --cov=challenge tests/model

.PHONY: api-test
api-test:			## Run tests and coverage
	mkdir reports || true
	pytest --cov-config=.coveragerc --cov-report term --cov-report html:reports/html --cov-report xml:reports/coverage.xml --junitxml=reports/junit.xml --cov=challenge tests/api

.PHONY: build
build:			## Build locally the python artifact
	python setup.py bdist_wheel

.PHONY: docker-build
docker-build:		## Build production Docker image
	docker build -t flight-delay-api .

.PHONY: docker-build-dev
docker-build-dev:	## Build development Docker image
	docker build -f Dockerfile.dev -t flight-delay-api-dev .

.PHONY: docker-run
docker-run:		## Run production API in Docker
	docker run -p 8000:8000 flight-delay-api

.PHONY: docker-run-dev
docker-run-dev:		## Run development API in Docker
	docker run -p 8001:8000 flight-delay-api-dev

.PHONY: docker-compose-up
docker-compose-up:	## Start all services with docker-compose
	docker-compose up --build

.PHONY: docker-compose-dev
docker-compose-dev:	## Start development service only
	docker-compose up --build api-dev

.PHONY: docker-compose-prod
docker-compose-prod:	## Start production service only
	docker-compose up --build api