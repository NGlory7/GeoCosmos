.PHONY: export preview grid data api web test

export:
	python -m pipeline.ee_export

preview:
	python -m pipeline.ee_export --preview

grid:
	python -m pipeline.features

data:
	python -m pipeline.build

api:
	uvicorn api.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	python -m pytest -q
