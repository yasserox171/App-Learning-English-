"""Role-based DRF permissions (master prompt §4).

Filled in Phase 2 alongside the User model's ``role`` field. Defined here
so the contract is visible from the start.
"""
from rest_framework.permissions import BasePermission


class _RolePermission(BasePermission):
    role: str = ""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == self.role
        )


class IsStudent(_RolePermission):
    role = "student"


class IsTeacher(_RolePermission):
    role = "teacher"


class IsAdmin(_RolePermission):
    role = "admin"
