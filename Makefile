lint:
	poetry run flake8 ./log_analyzer --max-line-length=120
	poetry run black ./log_analyzer --check --verbose --diff --color
	poetry run isort ./log_analyzer
	poetry run mypy ./log_analyzer

pytest:
	poetry run python -m pytest ./test -v
