.PHONY: install test clean run

UV := uv
PYTHON := python
PIP := pip

# Install the package in development mode
install:
	$(UV) run pip install -e ".[dev]"

# Run tests
test:
	pytest

# Run integration tests
test-integration:
	pytest tests/test_integration.py

# Run all tests
test-all:
	pytest tests/


clean:
	@echo "Cleaning build and distribution files..."
	if exist "build" echo Deleting build && rmdir /s /q "build"
	if exist "dist" echo Deleting dist && rmdir /s /q "dist"
	for /d %%d in (*.egg-info) do if exist "%%d" echo Deleting %%d && rmdir /s /q "%%d"
	if exist ".pytest_cache" echo Deleting .pytest_cache && rmdir /s /q ".pytest_cache"
	if exist ".coverage" echo Deleting .coverage && attrib -r .coverage & del ".coverage"
	if exist "coverage.xml" echo Deleting coverage.xml && attrib -r coverage.xml & del "coverage.xml"
	if exist "htmlcov" echo Deleting htmlcov && rmdir /s /q "htmlcov"
	for /d /r . %%d in (__pycache__) do @if exist "%%d" echo Deleting %%d && attrib -r "%%d" & rmdir /s /q "%%d"
	echo Deleting Python bytecode files
	del /s /q *.pyc 2>nul

# Run the server
run:
	$(UV) run run_server.py
