"""Converging trailing-stop bot — deterministic, API/AI-free safety layer.

Runs every 5 minutes (24/7), tightens stops as price climbs, and synthesizes
extended-hours stops via marketable limit sells when the regular session is
closed. See README.md for details.
"""
