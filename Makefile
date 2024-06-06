run-tests:
	python -m unittest discover -s tests

prepare-environment:
	python scripts/setup.py

check-code-format:
	black --check zksync2 scripts tests

format-code:
	black zksync2 scripts tests