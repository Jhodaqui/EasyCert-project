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

class ContratoModalForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["numero_contrato", "fecha_generacion", "fecha_inicio", "valor_pago", "archivo"]
        widgets = {
            "fecha_generacion": forms.DateInput(attrs={"type": "date"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_archivo(self):
        f = self.cleaned_data.get("archivo")
        if f:
            fname = f.name.lower()
            if not (fname.endswith(".pdf")):
                raise forms.ValidationError("Solo se permiten archivos PDF.")
        return f