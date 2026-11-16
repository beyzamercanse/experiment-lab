.PHONY: run test
run:
	python3 scripts/pipeline.py

test:
	python3 -m unittest discover -s tests -v
