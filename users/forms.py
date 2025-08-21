from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.core.files.storage import default_storage
from .models import CustomUser, TIPOS_DOCUMENTO, Constancia
from .validators import validate_pdf
from datetime import date

ALLOWED_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"}

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, required=True)

    nombre_completo = forms.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', "Solo letras y espacios")],
        label="Nombre completo"
    )
    tipo_documento = forms.ChoiceField(choices=TIPOS_DOCUMENTO, label="Tipo de documento")
    numero_documento = forms.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\d{1,15}$', "Solo números, máximo 15 dígitos")],
        label="Número de documento"
    )
    email = forms.EmailField(label="Correo electrónico")
    documento_pdf = forms.FileField(label="Documento (PDF)", required=True)

    class Meta:
        model = CustomUser
        fields = ["nombre_completo", "tipo_documento", "numero_documento", "email", "documento_pdf"]

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()
        domain = email.split("@")[-1]
        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise ValidationError("El correo debe ser de un dominio válido (gmail, outlook, hotmail, etc.)")
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    def clean_documento_pdf(self):
        f = self.cleaned_data.get("documento_pdf")
        if f:
            validate_pdf(f)
        return f

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.nombre_completo = self.cleaned_data["nombre_completo"]
        user.tipo_documento = self.cleaned_data["tipo_documento"]
        user.numero_documento = self.cleaned_data["numero_documento"]
        user.email = self.cleaned_data["email"].lower()
        user.set_password(self.cleaned_data["password1"])

        uploaded_file = self.cleaned_data.get("documento_pdf")
        if uploaded_file:
            folder = f"documents/{user.numero_documento}"
            target_name = f"{user.numero_documento}.pdf"
            target_path = f"{folder}/{target_name}"
            # eliminar existente para forzar overwrite
            if default_storage.exists(target_path):
                default_storage.delete(target_path)
            user.documento_pdf = uploaded_file

        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if not CustomUser.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("No existe un usuario activo con este correo.")
        return email
    
class ConstanciaForm(forms.Form):
    nombre_completo = forms.CharField(label="Nombre Completo", disabled=True)
    numero_documento = forms.CharField(label="Número Documento", disabled=True)
    tipo_documento = forms.CharField(label="Tipo Documento", disabled=True)
    email = forms.EmailField(label="Correo electrónico", disabled=True)

    fecha_inicial = forms.DateField(
        label="Fecha inicial de la constancia",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    fecha_final = forms.DateField(
        label="Fecha final de la constancia",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    tipo_constancia = forms.ChoiceField(
        label="Tipo de constancia",
        choices=[
            ("", "Seleccione...."),
            ("estudio", "Constancia de Estudio"),
            ("laboral", "Constancia Laboral"),
            ("un_dia", "Constancia por un solo día"),  # 👈 nueva opción
            ("otro", "Otro"),
        ]
    )

    # 🔹 Validaciones
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicial = cleaned_data.get("fecha_inicial")
        fecha_final = cleaned_data.get("fecha_final")
        tipo = cleaned_data.get("tipo_constancia")

        if fecha_inicial and fecha_final:
            # ❌ Caso 1: inicial después de final
            if fecha_inicial > fecha_final:
                self.add_error("fecha_inicial", "La fecha inicial no puede ser mayor que la fecha final.")
                self.add_error("fecha_final", "La fecha final no puede ser menor que la fecha inicial.")

            # ❌ Caso 2: fechas iguales (permitido solo si tipo = 'un_dia')
            if fecha_inicial == fecha_final and tipo != "un_dia":
                self.add_error("fecha_inicial", "Las fechas no pueden ser iguales (excepto en constancias de un solo día).")
                self.add_error("fecha_final", "Las fechas no pueden ser iguales (excepto en constancias de un solo día).")

        return cleaned_data

    def clean_tipo_constancia(self):
        tipo = self.cleaned_data.get("tipo_constancia")
        if not tipo:
            raise forms.ValidationError("Debe seleccionar un tipo de constancia.")
        return tipo