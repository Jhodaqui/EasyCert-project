from django import forms
from .models import Contrato

class ContratoUploadForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["archivo", "fecha_inicio", "fecha_fin", "obligaciones"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type":"date"}),
            "fecha_fin": forms.DateInput(attrs={"type":"date"}),
        }
