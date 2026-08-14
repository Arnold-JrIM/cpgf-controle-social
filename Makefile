.PHONY: install test lint app bootstrap-kaggle bootstrap-official
install:
	python -m pip install -e ".[dev]"
test:
	pytest
lint:
	ruff check src tests scripts streamlit_app.py pages
app:
	streamlit run streamlit_app.py
bootstrap-kaggle:
	python scripts/bootstrap_data.py --source kaggle --dry-run
bootstrap-official:
	python scripts/bootstrap_data.py --source official --dry-run
