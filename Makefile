.PHONY: setup data warehouse run clean

PY := .venv/bin/python

setup:            ## create venv + install deps
	python3 -m venv .venv && $(PY) -m pip install -U pip && $(PY) -m pip install -r requirements.txt

data:             ## generate the synthetic CRM dataset
	$(PY) src/generate_data.py

warehouse:        ## build the DuckDB warehouse (staging -> marts)
	$(PY) src/etl.py

run:              ## full pipeline: data -> models -> charts -> exports
	$(PY) src/run_all.py

clean:            ## remove generated data + db (keep committed charts)
	rm -f data/pipeline.duckdb data/raw/*.csv
	rm -rf data/exports
