import logging
from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def wagtail_login_redirect(request):
    """Redirect Wagtail admin login to OIDC authenticate."""
    # If user is already authenticated
    if request.user.is_authenticated:
        # Check if user has staff access
        if request.user.is_staff:
            logger.debug(f"User {request.user.username} has staff access, redirecting to admin")
            next_url = request.GET.get('next', '/admin/')
            return redirect(next_url)
        else:
            # User authenticated but no staff access (not in any Django group)
            logger.info(f"User {request.user.username} authenticated but has no staff access")
            messages.warning(
                request,
                f"Welcome {request.user.username}! Your account has been created successfully. "
                "To access the admin panel, please contact an administrator who will assign you to the appropriate group "
                "(Administrators, Reviewers, or Content Developers) in the Django Admin."
            )
            return redirect('/')
    
    # Otherwise, redirect to OIDC for authentication
    next_url = request.GET.get('next', '/admin/')
    return redirect(f'/oidc/authenticate/?next={next_url}')


def oidc_logout_view(request):
    """Custom logout view that also logs out from Keycloak."""
    # Get the ID token before logging out (needed for Keycloak logout)
    id_token = request.session.get('oidc_id_token')
    
    # Log out from Django (clears session)
    django_logout(request)
    
    # Build Keycloak logout URL
    if id_token and hasattr(settings, 'OIDC_OP_BASE_URL') and hasattr(settings, 'OIDC_REALM'):
        keycloak_logout_url = f"{settings.OIDC_OP_BASE_URL}/realms/{settings.OIDC_REALM}/protocol/openid-connect/logout"
        
        # Add post_logout_redirect_uri and id_token_hint parameters
        redirect_uri = request.build_absolute_uri('/')
        params = {
            'post_logout_redirect_uri': redirect_uri,
            'id_token_hint': id_token,
        }
        
        return HttpResponseRedirect(f"{keycloak_logout_url}?{urlencode(params)}")
    
    # Fallback to home if OIDC is not configured
    return redirect('/')
