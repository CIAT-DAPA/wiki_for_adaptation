from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from urllib.parse import urlencode


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
