from django.db import models
from django.conf import settings

# Create your models here.

def contrato_upload_path(instance, filename):
    return f"contracts/{instance.usuario.numero_documento}/{filename}"

class Contrato(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contratos")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    obligaciones = models.TextField(blank=True)
    archivo = models.FileField(upload_to=contrato_upload_path)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"Contrato {self.usuario.numero_documento} ({self.fecha_inicio} → {self.fecha_fin})"


class TempExtractedData(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    clave = models.CharField(max_length=255)
    valor = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[TEMP] {self.usuario.email} - {self.clave}"


class UserContractData(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    campo = models.CharField(max_length=255)
    valor = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("usuario", "campo")  # evita duplicados

    def __str__(self):
        return f"{self.usuario.email} - {self.campo}"

class Certificado(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificados_documentos")
    numero = models.PositiveIntegerField(unique=True)  # autoincremental
    archivo = models.FileField(upload_to="certificados/", blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Certificación N° {self.numero:03d} - {self.usuario.nombre_completo}"

    def numero_formateado(self):
        return f"{self.numero:03d}"  # Ejemplo: 001, 002, 003