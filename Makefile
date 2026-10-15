PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: install data sample agg figures site insights report test lint check

install:
	$(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m taxi_insights.download

sample:
	$(PYTHON) -m taxi_insights.sample

agg:
	$(PYTHON) -m taxi_insights.aggregate

figures:
	$(PYTHON) -m taxi_insights.figures

site:
	$(PYTHON) -m taxi_insights.dashboard

insights:
	$(PYTHON) -m taxi_insights.insights

report: agg figures site insights

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

check: lint test
