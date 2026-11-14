.PHONY: data api web test

data:
	python -m pipeline.build

api:
	uvicorn api.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	python -m pytest -q
