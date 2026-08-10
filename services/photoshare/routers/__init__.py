"""API routers for PhotoShare product features (albums, shares, comments, tags, analytics).

Each router is a thin FastAPI layer over the SQLAlchemy models already defined in
app_database.py. No schema changes -- these tables have existed since the initial
migration but had no API surface until now.
"""
