import os
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)
from django.conf import settings

TIPOS_DOCUMENTO = [
    ('CC', 'Cédula de ciudadanía'),
    ('TI', 'Tarjeta de identidad'),
    ('CE', 'Cédula de extranjería'),
    ('PA', 'Pasaporte'),
]

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("admin", "Administrador"),
        ("staff", "Funcionario"),
        ("user", "Usuario"),
    )

    # Nuevos campos
    nombres = models.CharField("Nombres", max_length=100)
    apellidos = models.CharField("Apellidos", max_length=100)
    tipo_documento = models.CharField("Tipo de documento", max_length=10, choices=TIPOS_DOCUMENTO)
    numero_documento = models.CharField("Número de documento", max_length=15, unique=True)
    email = models.EmailField("Correo electrónico", unique=True)

    # Roles
    role = models.CharField("Rol de usuario", max_length=20, choices=ROLE_CHOICES, default="user")

    # Estado
    is_active = models.BooleanField(default=True)  # <-- Ahora siempre activo por defecto
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos", "tipo_documento", "numero_documento"]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.numero_documento})"

    def get_tipo_documento_display_full(self):
        """Devuelve el texto completo del tipo de documento"""
        return dict(TIPOS_DOCUMENTO).get(self.tipo_documento, self.tipo_documento)
    
class Constancia(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_proceso", "En Proceso"),
        ("firmada", "Firmada"),
        ("rechazada", "Rechazada"),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_inicial = models.DateField()
    fecha_final = models.DateField()
    comentario = models.TextField(blank=True, null=True) 
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.usuario} ({self.fecha_inicial} → {self.fecha_final}) - {self.estado}"

class dptos(models.Model):
    idDepto = models.CharField(primary_key=True, max_length=20, unique=True)
    nombreDepto = models.CharField(max_length=100)

    def __str__(self):
        return self.nombreDepto

class municipios(models.Model):
    idMpio = models.AutoField(primary_key=True)
    nombreMpio = models.CharField(max_length=100)
    idDepto = models.ForeignKey(dptos, on_delete=models.CASCADE)
    nombreCentro = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombreMpio    
