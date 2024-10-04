default: test

detox-test:
	detox

test: env
	.venv/bin/pytest -x tests --cov=confetti --cov-report=html

env:
	uv venv
	uv pip install -e ".[testing]"

doc: env
	.venv/bin/sphinx-build -a -W -E doc build/sphinx/html

