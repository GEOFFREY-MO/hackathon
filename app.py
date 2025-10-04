"""
Compatibility entrypoint for Render or other hosts that run `gunicorn app:app`.

This simply re-exports the Flask app instance defined in `wsgi.py`.
"""

from wsgi import app  # noqa: F401


