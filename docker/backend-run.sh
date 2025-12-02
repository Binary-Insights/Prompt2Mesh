#!/bin/sh
# Simple wrapper to start the backend server
# This ensures environment variables are available to the Python process

cd /app
exec python3 src/backend/backend_server.py
