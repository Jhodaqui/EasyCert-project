from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.core.files.storage import default_storage
from .models import CustomUser, TIPOS_DOCUMENTO, Constancia
from datetime import date

# Dominios permitidos
ALLOWED_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "sena.edu.co"
}


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        required=True,
        min_length=5
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
        required=True
    )

    # Campos personalizados
    nombres = forms.CharField(
        max_length=100,
        validators=[RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', "Solo letras y espacios")],
        label="Nombres"
    )
    apellidos = forms.CharField(
        max_length=100,
        validators=[RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', "Solo letras y espacios")],
        label="Apellidos"
    )
    tipo_documento = forms.ChoiceField(
        choices=TIPOS_DOCUMENTO,
        label="Tipo de documento"
    )
    numero_documento = forms.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\d{1,15}$', "Solo números, máximo 15 dígitos")],
        label="Número de documento"
    )
    email = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = CustomUser
        fields = ["nombres", "apellidos", "tipo_documento", "numero_documento", "email"]

    # Validación de correo
    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        domain = email.split("@")[-1]

        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise ValidationError(
                "El correo debe ser de un dominio válido: Gmail, Outlook, Hotmail, sena.edu.co, etc."
            )
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    # Validación de contraseñas
    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Las contraseñas no coinciden.")
        return cleaned

    # Guardar usuario
    def save(self, commit=True):
        user = super().save(commit=False)
        user.nombres = self.cleaned_data["nombres"]
        user.apellidos = self.cleaned_data["apellidos"]
        user.tipo_documento = self.cleaned_data["tipo_documento"]
        user.numero_documento = self.cleaned_data["numero_documento"]
        user.email = self.cleaned_data["email"].lower()
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()
        return user

class BulkUploadForm(forms.Form):
    file = forms.FileField(
        label="Archivo de usuarios (CSV o Excel)",
        help_text="Sube un archivo con columnas: nombres, apellidos, tipo_documento, numero_documento, email, password"
    )

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

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicial = cleaned_data.get("fecha_inicial")
        fecha_final = cleaned_data.get("fecha_final")

        if fecha_inicial and fecha_final:
            if fecha_inicial > fecha_final:
                self.add_error("fecha_inicial", "La fecha inicial no puede ser mayor que la fecha final.")
                self.add_error("fecha_final", "La fecha final no puede ser menor que la fecha inicial.")

        return cleaned_data