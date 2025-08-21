import os
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.utils import timezone

TIPOS_DOCUMENTO = [
    ('CC', 'Cédula de ciudadanía'),
    ('TI', 'Tarjeta de identidad'),
    ('CE', 'Cédula de extranjería'),
    ('PA', 'Pasaporte'),
]

def user_document_upload_path(instance, filename):
    # Forzamos extensión .pdf y nombre como numero_documento.pdf
    ext = '.pdf'
    filename = f"{instance.numero_documento}{ext}"
    return os.path.join("documents", filename)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not password:
            raise ValueError("Superuser debe tener contraseña")
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    nombre_completo = models.CharField(max_length=150)
    tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO)
    numero_documento = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    documento_pdf = models.FileField(upload_to=user_document_upload_path, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo", "tipo_documento", "numero_documento"]

    def __str__(self):
        return self.email