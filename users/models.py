import os
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)

TIPOS_DOCUMENTO = [
    ('CC', 'Cédula de ciudadanía'),
    ('TI', 'Tarjeta de identidad'),
    ('CE', 'Cédula de extranjería'),
    ('PA', 'Pasaporte'),
]

def user_document_upload_path(instance, filename):
    """
    Ruta: media/documents/<numero_documento>/<numero_documento>.pdf
    Forzamos .pdf; instance.numero_documento debe estar asignado antes de guardar.
    """
    ext = '.pdf'
    num = str(instance.numero_documento)
    num = "".join(ch for ch in num if ch.isalnum())
    filename = f"{num}{ext}"
    return os.path.join("documents", num, filename)


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
        extra_fields.setdefault("is_active", True)
        if not password:
            raise ValueError("Superuser debe tener contraseña")
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    nombre_completo = models.CharField("Nombres completos", max_length=150)
    tipo_documento = models.CharField("Tipo de documento", max_length=10, choices=TIPOS_DOCUMENTO)
    numero_documento = models.CharField("Número de documento", max_length=15, unique=True)
    email = models.EmailField("Correo electrónico", unique=True)
    documento_pdf = models.FileField("Copia documento (PDF)", upload_to=user_document_upload_path, null=True, blank=True)

    is_active = models.BooleanField(default=False)  # por defecto inactivo hasta activar
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre_completo", "tipo_documento", "numero_documento"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.numero_documento})"