.PHONY: test install

test:
	PYTHONPATH=src pytest -q

install:
	pip install -e ".[dev]"
