from django.db import models
from django.conf import settings

# Create your models here.

def contrato_upload_path(instance, filename):
    return f"contracts/{instance.usuario.numero_documento}/{filename}"

class Contrato(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contratos")
    numero_contrato = models.CharField(max_length=100, blank=True, null=True)   # manual
    fecha_generacion = models.DateField(blank=True, null=True)  # manual
    fecha_inicio = models.DateField(blank=True, null=True)      # manual
    fecha_fin = models.DateField(blank=True, null=True)         # extraído (plazo)
    objeto = models.TextField(blank=True, null=True)            # extraído
    obligaciones = models.TextField(blank=True, null=True)      # extraído
    objetivos_especificos = models.TextField(blank=True, null=True)  # extraído (si aplica)
    valor_pago = models.CharField(max_length=200, blank=True, null=True)  # manual o extraído
    archivo = models.FileField(upload_to=contrato_upload_path, blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
        unique_together = ("usuario", "numero_contrato")  # evita duplicados

    def __str__(self):
        return f"Contrato {self.numero_contrato or self.usuario.numero_documento}"


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
