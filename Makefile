run-tests:
	python -m unittest discover -s tests

prepare-test:
	python scripts/setup.py

check-code-format:
	black --check zksync2 scripts tests

format-code:
	black zksync2 scripts tests

wait:
	python scripts/wait.py