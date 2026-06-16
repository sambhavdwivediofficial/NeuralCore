.DEFAULT_GOAL := help
SHELL         := cmd.exe
PYTHON        := py -3.13
BACKEND_DIR   := backend
RUST_DIR      := rust_engine

.PHONY: help install install-dev install-worker lint format typecheck test test-unit \
        test-integration coverage rust-build rust-test rust-bench rust-audit \
        rust-install api worker beat clean deep-clean docs

help:
	@echo.
	@echo  NeuralCore — Developer Commands
	@echo  ================================
	@echo.
	@echo  Setup:
	@echo    make install          Install runtime dependencies
	@echo    make install-dev      Install dev + lint tools
	@echo    make install-worker   Install GPU/ML worker deps
	@echo    make rust-install     Build + install Rust engine (neuralcore_engine)
	@echo.
	@echo  Quality:
	@echo    make lint             Run ruff linter
	@echo    make format           Auto-format with ruff
	@echo    make typecheck        Run mypy type checker
	@echo    make test             Run all unit tests
	@echo    make test-unit        Run fast unit tests only
	@echo    make test-integration Run integration tests (needs services)
	@echo    make coverage         Run tests with coverage report
	@echo.
	@echo  Run:
	@echo    make api              Start FastAPI dev server
	@echo    make worker           Start Celery worker
	@echo    make beat             Start Celery beat scheduler
	@echo.
	@echo  Rust:
	@echo    make rust-build       Build Rust engine (release)
	@echo    make rust-test        Run Rust unit tests
	@echo    make rust-bench       Run Criterion benchmarks
	@echo    make rust-audit       Security audit (cargo audit)
	@echo.
	@echo  Misc:
	@echo    make docs             Serve MkDocs documentation
	@echo    make clean            Remove build artifacts
	@echo    make deep-clean       Remove everything including deps
	@echo.

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements-prod.txt

install-dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt

install-worker:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r $(BACKEND_DIR)/requirements-worker.txt

rust-build:
	cd $(RUST_DIR) && cargo build --release --features python-bindings

rust-install:
	$(PYTHON) -m pip install maturin
	cd $(RUST_DIR) && maturin develop --release --features python-bindings

rust-test:
	cd $(RUST_DIR) && cargo test --all-features -- --test-threads=4

rust-bench:
	cd $(RUST_DIR) && cargo bench --features benchmarks

rust-audit:
	cd $(RUST_DIR) && cargo audit

lint:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check .

format:
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format .
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check --fix .

typecheck:
	cd $(BACKEND_DIR) && $(PYTHON) -m mypy . --ignore-missing-imports

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v

test-unit:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v -m "not integration and not slow"

test-integration:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v -m integration

coverage:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

api:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd $(BACKEND_DIR) && $(PYTHON) -m celery -A task_queue.celery.celery_app worker --loglevel=info --concurrency=4

beat:
	cd $(BACKEND_DIR) && $(PYTHON) -m celery -A task_queue.celery.celery_app beat --loglevel=info

docs:
	$(PYTHON) -m mkdocs serve --dev-addr=127.0.0.1:8080

clean:
	if exist $(BACKEND_DIR)\__pycache__ rd /s /q $(BACKEND_DIR)\__pycache__
	if exist $(RUST_DIR)\target\debug rd /s /q $(RUST_DIR)\target\debug
	if exist .pytest_cache rd /s /q .pytest_cache
	if exist htmlcov rd /s /q htmlcov
	for /r $(BACKEND_DIR) %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d"
	for /r $(BACKEND_DIR) %%f in (*.pyc) do if exist "%%f" del /q "%%f"

deep-clean: clean
	if exist $(RUST_DIR)\target rd /s /q $(RUST_DIR)\target
	$(PYTHON) -m pip freeze > _tmp_freeze.txt
	$(PYTHON) -m pip uninstall -r _tmp_freeze.txt -y
	del /q _tmp_freeze.txt
	