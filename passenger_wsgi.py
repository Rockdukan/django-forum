import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

PROJECT_ROOT = Path(__file__).resolve().parent

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "core.settings.production"))
os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

application = get_wsgi_application()
