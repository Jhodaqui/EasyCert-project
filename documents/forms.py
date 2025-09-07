from django import forms
from .models import Contrato

class ContratoUploadForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["archivo", "fecha_inicio", "fecha_fin"]
        widgets = {
            "fecha_inicio": forms.TextInput(attrs={"type": "text", "placeholder": "dd/mm/aaaa"}),
            "fecha_fin": forms.TextInput(attrs={"type": "text", "placeholder": "dd/mm/aaaa"}),
        }

class ContratoModalForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = [
            "numero_contrato",
            "fecha_generacion",
            "fecha_inicio",
            "fecha_fin",
            "valor_pago",
            "objeto",
            "archivo",
            "objetivos_especificos",
        ]
        widgets = {
            "fecha_generacion": forms.TextInput(attrs={"type": "text", "placeholder": "dd/mm/aaaa"}),
            "fecha_inicio": forms.TextInput(attrs={"type": "text", "placeholder": "dd/mm/aaaa"}),
            "fecha_fin": forms.TextInput(attrs={"type": "text", "placeholder": "dd/mm/aaaa"}),
            "objeto": forms.Textarea(attrs={"rows": 3, "cols": 40}),
        }

    def clean_archivo(self):
        f = self.cleaned_data.get("archivo")
        if f:
            if not f.name.lower().endswith(".pdf"):
                raise forms.ValidationError("Solo se permiten archivos PDF.")
        return f