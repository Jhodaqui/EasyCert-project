from django.db import models
from django.conf import settings
from documents.models import Contrato
import os

# Create your models here.

class Certificado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificados_staff")
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    numero = models.PositiveIntegerField(unique=True, null=True, blank=True)  # 🔹 consecutivo
    archivo = models.FileField(upload_to="certificates/")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Certificado {self.usuario.numero_documento} - {self.creado_en.date()}"

    def numero_formateado(self):
        return str(self.numero).zfill(3) if self.numero else "---"