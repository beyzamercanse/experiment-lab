.PHONY: run robustness test
run:
	python3 scripts/pipeline.py

robustness: run
	python3 scripts/robustness.py

test:
	python3 -m unittest discover -s tests -v
