# Project Makefile for trilodocx
# Usage:
#   make serve      # Start the FastAPI development server
#   make format     # Format Python files with ruff
#   make lint       # Run ruff lint checks
#   make typecheck  # Run type checking (mypy or pyright if installed)
#   make test       # Run pytest
#   make check      # Run lint, typecheck, and tests
#   make install    # Create virtual environment and install dependencies

PYTHON = .venv/bin/python
RUFF = .venv/bin/ruff
UVICORN = .venv/bin/uvicorn
PYTEST = .venv/bin/pytest

.PHONY: install serve format lint typecheck test check

serve:
	$(UVICORN) app.main:app --reload

format:
	$(RUFF) format .

lint:
	$(RUFF) check .

typecheck:
	@if [ -x "$(PYTHON)" ] && $(PYTHON) -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mypy') else 1)" >/dev/null 2>&1; then \
		$(PYTHON) -m mypy app tests; \
	elif [ -x .venv/bin/pyright ]; then \
		.venv/bin/pyright app tests; \
	else \
		echo "No type checker installed. Install mypy or pyright in the venv."; exit 1; \
	fi

test:
	$(PYTEST) -q

UV = uv

install:
	$(UV) venv .venv
	$(UV) sync

check: lint typecheck test
