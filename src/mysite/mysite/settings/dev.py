from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure--$iu)jzl*%l1+(6#=6l^xen9_5b6gqig^_sp0pw19b$qw))ynz"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Session configuration for OIDC (allow cookies in development)
SESSION_COOKIE_SAMESITE = None  # Allow cross-site cookies for OIDC callback
SESSION_COOKIE_SECURE = False  # Not HTTPS in development
CSRF_COOKIE_SAMESITE = None
CSRF_COOKIE_SECURE = False

# Forzar backend de sesión a base de datos para OIDC en local
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

import logging
logging.basicConfig(level=logging.DEBUG)

# Configure detailed OIDC logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'mozilla_django_oidc': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

print("[OIDC DEBUG] OIDC_RP_CLIENT_ID:", repr(OIDC_RP_CLIENT_ID))
print("[OIDC DEBUG] OIDC_REALM:", repr(OIDC_REALM))
print("[OIDC DEBUG] OIDC_RP_CLIENT_SECRET:", repr(OIDC_RP_CLIENT_SECRET))
print("[OIDC DEBUG] SESSION_ENGINE:", SESSION_ENGINE)
# Enable OIDC backend in development only when all required env vars are present
# (client id, realm, and client secret). This avoids half-configured OIDC.
if OIDC_RP_CLIENT_ID and OIDC_REALM and OIDC_RP_CLIENT_SECRET:
    print("[OIDC DEBUG] ✓ OIDC IS ACTIVE - Backend and LOGIN_URL configured")
    AUTHENTICATION_BACKENDS = (
        "mysite.oidc_backend.KeycloakOIDCBackend",
        "django.contrib.auth.backends.ModelBackend",
    )
    LOGIN_URL = "/oidc/authenticate/"
    LOGIN_REDIRECT_URL = "/admin/"
    LOGOUT_REDIRECT_URL = "/"
    
    # Configure Wagtail to use the OIDC login URL instead of its own
    WAGTAIL_FRONTEND_LOGIN_URL = "/oidc/authenticate/"
    WAGTAILADMIN_LOGIN_URL = "/oidc/authenticate/"
    
    # Configure custom logout to close Keycloak session
    WAGTAIL_FRONTEND_LOGOUT_URL = "/logout/"
    WAGTAILADMIN_LOGOUT_URL = "/logout/"
else:
    print("[OIDC DEBUG] ✗ OIDC NOT ACTIVE - Missing env vars")


try:
    from .local import *
except ImportError:
    pass
