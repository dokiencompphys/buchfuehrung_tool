"""Einstiegspunkt: `uv run uvicorn buchfuehrung.main:app --reload --host 0.0.0.0`"""

from buchfuehrung.api.app import create_app

app = create_app()
