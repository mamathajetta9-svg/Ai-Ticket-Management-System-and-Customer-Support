from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


class CustomUserManager(UserManager):

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields['role'] = 'ADMIN'
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True

        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields
        )


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        AGENT = 'AGENT', 'Agent'
        CUSTOMER = 'CUSTOMER', 'Customer'

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.username} ({self.role})"