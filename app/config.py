# app/config.py
import os

GROK_API_KEY = os.environ.get("GROK_API_KEY", "")  # Set this in your environment variables
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")  # Set this in your environment variables
UPLOAD_DIR = "uploads"
