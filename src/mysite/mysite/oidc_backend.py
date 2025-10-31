from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
    """Map Keycloak roles to Django groups on login."""

    def filter_users_by_claims(self, claims):
        email = claims.get("email")
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email)

    def create_user(self, claims):
        """Create user with proper field mapping from Keycloak claims."""
        email = claims.get("email")
        username = claims.get("preferred_username", email)
        
        user = self.UserModel.objects.create_user(username=username, email=email)
        
        # Map user fields from Keycloak claims
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.is_staff = True
        user.is_active = True
        
        # Check if user has Administrator role and make superuser
        roles = self._get_roles_from_claims(claims)
        if "Administrator" in roles:
            user.is_superuser = True
        
        user.save()
        self._apply_groups_and_permissions(user, claims)
        return user

    def update_user(self, user, claims):
        """Update user fields from Keycloak claims on each login."""
        # Update user fields from claims
        user.first_name = claims.get("given_name", "")
        user.last_name = claims.get("family_name", "")
        user.email = claims.get("email", user.email)
        
        # Update username if preferred_username changed
        preferred_username = claims.get("preferred_username")
        if preferred_username and preferred_username != user.username:
            # Only update if new username doesn't conflict
            if not self.UserModel.objects.filter(username=preferred_username).exclude(pk=user.pk).exists():
                user.username = preferred_username
        
        # Ensure user remains active and staff
        user.is_staff = True
        user.is_active = True
        
        # Update superuser status based on Administrator role
        roles = self._get_roles_from_claims(claims)
        user.is_superuser = "Administrator" in roles
        
        user.save()
        self._apply_groups_and_permissions(user, claims)
        return user
    
    def _get_roles_from_claims(self, claims):
        """Extract Keycloak realm roles from claims."""
        roles = []
        realm_access = claims.get("realm_access", {})
        if isinstance(realm_access, dict):
            roles = realm_access.get("roles", []) or []
        return roles

    def _apply_groups_and_permissions(self, user, claims):
        """Map Keycloak roles to Django groups and assign permissions."""
        roles = self._get_roles_from_claims(claims)
        
        desired = set(r for r in roles if r in {"Administrator", "Reviewer", "ContentDeveloper"})
        
        # Map roles to groups and assign Wagtail permissions
        for role in ["Administrator", "Reviewer", "ContentDeveloper"]:
            group, created = Group.objects.get_or_create(name=role)
            
            # Add role-specific permissions
            if created or not group.permissions.exists():
                self._configure_group_permissions(group, role)
            
            if role in desired:
                group.user_set.add(user)
            else:
                group.user_set.remove(user)

    def _configure_group_permissions(self, group, role):
        """Configure permissions for each role according to requirements."""
        # Base permission: access Wagtail admin
        try:
            admin_permission = Permission.objects.get(
                content_type__app_label='wagtailadmin',
                codename='access_admin'
            )
            group.permissions.add(admin_permission)
        except Permission.DoesNotExist:
            pass

        # Get content types for Page and related models
        from wagtail.models import Page
        page_ct = ContentType.objects.get_for_model(Page)
        
        if role == "Administrator":
            # Full permissions: create, edit, publish, delete pages and access settings
            perms = Permission.objects.filter(
                content_type__app_label__in=['wagtailcore', 'wagtailadmin', 'wagtailimages', 'wagtaildocs']
            )
            group.permissions.add(*perms)
            
        elif role == "Reviewer":
            # Can view, edit (lock/unlock), publish, and approve workflows
            reviewer_perms = Permission.objects.filter(
                content_type=page_ct,
                codename__in=['change_page', 'publish_page', 'lock_page', 'unlock_page']
            )
            group.permissions.add(*reviewer_perms)
            # Add workflow approval permission
            try:
                approve_task = Permission.objects.get(
                    content_type__app_label='wagtailcore',
                    codename='approve_task'
                )
                group.permissions.add(approve_task)
            except Permission.DoesNotExist:
                pass
                
        elif role == "ContentDeveloper":
            # Can create, edit, and submit for review (but not publish)
            dev_perms = Permission.objects.filter(
                content_type=page_ct,
                codename__in=['add_page', 'change_page']
            )
            group.permissions.add(*dev_perms)
            # Add image and document upload permissions
            try:
                img_perms = Permission.objects.filter(
                    content_type__app_label='wagtailimages',
                    codename__in=['add_image', 'change_image']
                )
                doc_perms = Permission.objects.filter(
                    content_type__app_label='wagtaildocs',
                    codename__in=['add_document', 'change_document']
                )
                group.permissions.add(*img_perms)
                group.permissions.add(*doc_perms)
            except:
                pass

    def _add_wagtail_admin_permission(self, group):
        """Add 'Can access Wagtail admin' permission to the group."""
        try:
            # Wagtail admin access permission
            admin_permission = Permission.objects.get(
                content_type__app_label='wagtailadmin',
                codename='access_admin'
            )
            group.permissions.add(admin_permission)
        except Permission.DoesNotExist:
            # If permission doesn't exist, try to create it or skip
            pass
