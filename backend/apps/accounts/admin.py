from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'id',
        'username',
        'email',
        'role',
        'is_active',
        'is_staff',
    )

    list_filter = ('role', 'is_active', 'is_staff')

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('role',)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('email', 'role')
        }),
    )