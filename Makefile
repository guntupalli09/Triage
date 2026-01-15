# Makefile for experiments

.PHONY: experiments clean-experiments

experiments:
	python experiments/run_all.py

clean-experiments:
	rm -rf experiments/artifacts/*
	rm -rf experiments/results/*
	rm -f experiments/RESULTS.md

clean-data:
	rm -rf experiments/data/ndas/*.txt
	rm -rf experiments/data/ndas/*.json

clean-all: clean-experiments clean-data
