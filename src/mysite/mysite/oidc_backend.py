import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
    """
    OIDC Authentication Backend for Keycloak.
    
    - Keycloak is used ONLY for authentication (login)
    - Authorization (roles/permissions) is managed in Django Admin via Groups
    - New users have no admin access until assigned to a group by an administrator
    """

    def filter_users_by_claims(self, claims):
        """Find the existing user for these claims.

        Primary match is by email, but Keycloak may send a different/empty email
        than what we stored (e.g. email changed, unverified, or no email mapper).
        In that case we fall back to matching by ``preferred_username`` so we
        reuse the existing account instead of trying to create a duplicate
        (which would collide on the unique username constraint).
        """
        email = claims.get("email")
        username = claims.get("preferred_username")

        if email:
            users = self.UserModel.objects.filter(email__iexact=email)
            if users.exists():
                return users

        if username:
            return self.UserModel.objects.filter(username__iexact=username)

        return self.UserModel.objects.none()

    def create_user(self, claims):
        """Create user from Keycloak claims. No admin access by default."""
        email = claims.get("email")
        username = claims.get("preferred_username", email)

        # Safety net: if a user with this username already exists (e.g. the email
        # changed so the lookup above missed it), reuse and update it instead of
        # raising a duplicate-key IntegrityError.
        existing = self.UserModel.objects.filter(username__iexact=username).first()
        if existing:
            logger.info(f"OIDC user '{username}' already exists; updating instead of creating")
            return self.update_user(existing, claims)

        logger.info(f"Creating OIDC user: {username} / {email}")

        user = self.UserModel.objects.create_user(username=username, email=email)
        
        # Map user fields from Keycloak claims
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.is_active = True
        
        # NEW USERS: No admin access by default
        # Administrator must assign them to a group in Wagtail Admin
        user.is_staff = False
        user.is_superuser = False
        user.save()
        
        logger.info(f"User created: {user.username} (staff={user.is_staff}, superuser={user.is_superuser})")
        logger.info(f"User needs to be assigned to a group by an administrator in Wagtail Admin")
        
        return user

    def update_user(self, user, claims):
        """Update user fields and permissions based on Django groups."""
        logger.debug(f"Updating user: {user.username}")
        
        # Update user fields from claims
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.email = claims.get("email", user.email)
        
        # Update username if preferred_username changed
        preferred_username = claims.get("preferred_username")
        if preferred_username and preferred_username != user.username:
            if not self.UserModel.objects.filter(username=preferred_username).exclude(pk=user.pk).exists():
                user.username = preferred_username
        
        # Ensure user remains active
        user.is_active = True
        
        # Grant access based on Django groups (managed in Wagtail admin).
        # IMPORTANT: only ELEVATE here, never auto-downgrade. Earlier this method
        # reset is_staff/is_superuser to False on every login when the user was
        # not in a recognised group, which silently wiped access that an admin had
        # granted manually (via the staff/superuser checkboxes). To revoke access,
        # an admin removes the group / unchecks the flag in the admin and it now
        # persists.
        user_groups = set(user.groups.values_list('name', flat=True))

        if 'Administrators' in user_groups:
            user.is_staff = True
            user.is_superuser = True
        elif user_groups & {'Reviewers', 'Content Developers'}:
            user.is_staff = True

        user.save()
        logger.debug(f"User updated: {user.username} (staff={user.is_staff}, superuser={user.is_superuser})")
        logger.debug(f"User groups: {list(user_groups)}")
        
        return user

