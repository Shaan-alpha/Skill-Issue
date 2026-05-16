"""Vercel Functions entry point.

The @vercel/python runtime auto-detects an ASGI ``app`` at module level
when the file lives under ``api/``. Re-export the FastAPI app so we don't
duplicate the application wiring.
"""

from app.main import app

__all__ = ["app"]
