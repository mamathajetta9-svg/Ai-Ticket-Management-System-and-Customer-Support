from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    """Base class for role-based API permissions."""

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
