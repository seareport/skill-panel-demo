list:
	@LC_ALL=C $(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'

init:
	poetry install --sync
	pre-commit install

style:
	pre-commit run black -a

lint:
	pre-commit run ruff -a

mypy:
	dmypy run skill-panel

deps:
	pre-commit run poetry-lock -a
	pre-commit run poetry-export -a

serve:
	python -mpanel serve *app.py --autoreload --allow-websocket-origin=127.0.0.1:5006

heroku:
	python -mpanel serve --address="0.0.0.0" *app.py --autoreload --allow-websocket-origin=skill-panel-3607dfd2cee1.herokuapp.com --use-xheaders
