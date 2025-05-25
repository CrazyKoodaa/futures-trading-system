.PHONY: help setup install test lint clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  setup       - Set up development environment"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  clean       - Clean temporary files"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up   - Start Docker services"
	@echo "  docker-down - Stop Docker services"

setup:
	python -m venv venv
	./venv/Scripts/activate && pip install -r requirements.txt
	cp .env.template .env

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=.

lint:
	flake8 --max-line-length=100 .
	black --check .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
