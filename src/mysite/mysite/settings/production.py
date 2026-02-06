from .base import *
import os

DEBUG = False

# Security settings for production
ALLOWED_HOSTS = [
    'trackadapt.org',
    'www.trackadapt.org',
]

# Trust X-Forwarded-Proto header from reverse proxy
# CRITICAL: This tells Django to build redirect URIs with https://
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Wagtail base URL for production (MUST be HTTPS)
WAGTAILADMIN_BASE_URL = "https://trackadapt.org"

# OIDC settings for production
OIDC_VERIFY_SSL = True  # Verify SSL certificates in production

# Security headers (can be adjusted based on your setup)
# Since you're behind a reverse proxy, some of these might be handled there
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

try:
    from .local import *
except ImportError:
    pass
