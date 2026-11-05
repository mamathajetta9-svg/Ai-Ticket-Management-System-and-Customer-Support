from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    """Base permission that checks an authenticated user's active role."""

    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in self.allowed_roles
        )


class IsAdmin(RolePermission):
    allowed_roles = ("ADMIN",)


class IsAgent(RolePermission):
    allowed_roles = ("AGENT",)


class IsCustomer(RolePermission):
    allowed_roles = ("CUSTOMER",)


class IsAdminOrAgent(RolePermission):
    allowed_roles = ("ADMIN", "AGENT")


class IsAdminOrReadOnly(BasePermission):
    """Allow safe requests to authenticated users and writes to admins only."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return request.method in ("GET", "HEAD", "OPTIONS") or user.role == "ADMIN"
