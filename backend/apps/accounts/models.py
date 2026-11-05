from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    """User manager that keeps privileged account flags consistent."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.CUSTOMER)
        # Application roles do not automatically grant Django staff access.
        if extra_fields.get("role") != User.Role.ADMIN:
            extra_fields.setdefault("is_staff", False)
            extra_fields.setdefault("is_superuser", False)
        if email:
            email = self.normalize_email(email).strip().lower()
        return super().create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields["role"] = User.Role.ADMIN
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        AGENT = "AGENT", "Agent"
        CUSTOMER = "CUSTOMER", "Customer"

    email = models.EmailField(unique=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        # A role is an application authorization attribute, not a Django staff flag.
        # Only create_superuser / an explicitly managed staff account may access admin.
        if self.role != self.Role.ADMIN and self.is_superuser:
            self.is_superuser = False
            # A partial save must persist the privilege downgrade as well.
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"is_superuser"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
