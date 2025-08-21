from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from .models import CustomUser, TIPOS_DOCUMENTO
from .validators import validate_pdf

ALLOWED_EMAIL_DOMAINS = {"gmail.com","yahoo.com","outlook.com","hotmail.com","icloud.com"}

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
        # Guardamos en 2 pasos para asegurar que numero_documento está establecido antes de guardar el archivo
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.numero_documento = self.cleaned_data["numero_documento"]
        user.nombre_completo = self.cleaned_data["nombre_completo"]
        user.tipo_documento = self.cleaned_data["tipo_documento"]
        user.set_password(self.cleaned_data["password1"])

        # Asignamos el archivo al campo del modelo: Django llamará upload_to y usará numero_documento
        uploaded_file = self.cleaned_data.get("documento_pdf")
        if uploaded_file:
            user.documento_pdf = uploaded_file

        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
