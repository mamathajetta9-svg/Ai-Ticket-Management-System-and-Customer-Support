from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        ("Application authorization", {"fields": ("role", "google_id")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Account details", {"fields": ("email", "role")}),
    )
