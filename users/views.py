from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, LoginForm, ConstanciaForm, Constancia
from .models import CustomUser

# Create your views here.

# Registro
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            if request.FILES.get("documento_pdf"):
                user.documento_pdf = request.FILES["documento_pdf"]
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(f"/users/activate/{uid}/{token}/")

            subject = "Activa tu cuenta EasyCert"
            message = render_to_string("users/emails/activation_email.txt", {"user": user, "activation_link": activation_link})
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)

            messages.success(request, "Registro realizado. Revisa tu correo para activar la cuenta.")
            return redirect("login")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = RegisterForm()
    return render(request, "users/register.html", {"form": form})


# Activación
def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(request, "Cuenta activada. Ahora puedes iniciar sesión.")
        else:
            messages.info(request, "Tu cuenta ya estaba activada.")
        return redirect("login")
    else:
        messages.error(request, "El enlace de activación no es válido o ha expirado.")
        return render(request, "users/activation_invalid.html")


# Reenviar activación
def resend_activation(request):
    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        try:
            user = CustomUser.objects.get(email=email)
            if user.is_active:
                messages.warning(request, "La cuenta ya está activa. No se reenviará activación.")
                return redirect("login")
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            activation_link = request.build_absolute_uri(f"/users/activate/{uid}/{token}/")
            subject = "Reenvío: activa tu cuenta EasyCert"
            message = render_to_string("users/emails/activation_email.txt", {"user": user, "activation_link": activation_link})
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            messages.success(request, "Correo de activación reenviado. Revisa tu bandeja.")
            return redirect("login")
        except CustomUser.DoesNotExist:
            messages.error(request, "No existe cuenta con ese correo.")
    return render(request, "users/resend_activation.html")



# Login
def login_view(request):
    form = LoginForm(request.POST or None)
    field_errors = {}  # Diccionario para errores específicos por campo

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, email=email, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Bienvenido {user.nombre_completo}")

                    # Redirección según rol
                    if user.role == "admin":
                        return redirect("admin_dashboard")
                    elif user.role == "staff":
                        return redirect("staff_dashboard")
                    else:
                        return redirect("user_dashboard")
                else:
                    # Error específico para cuenta no activada
                    field_errors['general'] = "⏳ Tu cuenta aún no está activada. Por favor, revisa tu correo electrónico para activarla."
                    # messages.error(request, "Tu cuenta aún no está activada. Revisa tu correo.")  # ELIMINADO
            else:
                # Error específico para credenciales incorrectas
                field_errors['general'] = "🔒 Correo electrónico o contraseña incorrectos. Verifica tus credenciales e intenta nuevamente."
                # messages.error(request, "Correo o contraseña incorrectos.")  # ELIMINADO
        else:
            # Capturar errores de validación del formulario por campo
            for field, errors in form.errors.items():
                field_errors[field] = " ".join(errors)
    
    # Enviamos el form y los errores al template
    return render(request, "users/login.html", {
        "form": form,
        "field_errors": field_errors
    })


# Logout
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión.")
    return redirect("login")


# Home (dashboard simple)
@login_required
def home_view(request):
    return render(request, "home.html")


# Password reset request
from django.utils.encoding import force_str
def password_reset_request_view(request):
    from .forms import PasswordResetRequestForm
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            user = CustomUser.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(f"/users/reset/{uid}/{token}/")
            subject = "Restablecer contraseña EasyCert"
            message = render_to_string("users/emails/password_reset_email.txt", {"user": user, "reset_link": reset_link})
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            messages.success(request, "Se envió un enlace para restablecer la contraseña (revisa la consola en desarrollo).")
            return redirect("login")
    else:
        form = PasswordResetRequestForm()
    return render(request, "users/password_reset_request.html", {"form": form})


# Password reset confirm
from django.contrib.auth.hashers import make_password
def password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == "POST":
            p1 = request.POST.get("password1")
            p2 = request.POST.get("password2")
            if p1 != p2:
                messages.error(request, "Las contraseñas no coinciden.")
            elif len(p1) < 4:  # regla mínima relajada
                messages.error(request, "La contraseña debe tener al menos 4 caracteres.")
            else:
                user.set_password(p1)
                user.save()
                messages.success(request, "Contraseña cambiada correctamente. Ya puedes iniciar sesión.")
                return redirect("login")
        return render(request, "users/password_reset_confirm.html", {"validlink": True})
    messages.error(request, "El enlace no es válido o ha expirado.")
    return redirect("password_reset")

# vistas segun roles
@login_required
def admin_dashboard(request):
    return render(request, "users/admin/dashboard.html")

@login_required
def staff_dashboard(request):
    # Aquí puedes filtrar según permisos/rol
    solicitudes = Constancia.objects.all().order_by("-creado_en")

    return render(request, "users/staff/dashboard.html", {"solicitudes": solicitudes})

@login_required
def user_dashboard(request):
    user = request.user  # usuario autenticado

    # Inicializamos el formulario con los datos del usuario
    initial_data = {
        "nombre_completo": user.nombre_completo,
        "numero_documento": user.numero_documento,
        "tipo_documento": user.tipo_documento,
        "email": user.email,
    }

    form_valido = False  # bandera para saber si el form pasó las validaciones

    if request.method == "POST":
        form = ConstanciaForm(request.POST, initial=initial_data)
        if form.is_valid():
            # 👉 aquí guardarías la solicitud en BD
            # print("Solicitud válida:", form.cleaned_data)
            constancia = Constancia.objects.create(
                usuario=user,
                fecha_inicial=form.cleaned_data["fecha_inicial"],
                fecha_final=form.cleaned_data["fecha_final"],
                tipo_constancia=form.cleaned_data["tipo_constancia"],
            )
            form_valido = True
            return redirect("user_dashboard") 

            # Marcamos bandera para que la plantilla muestre modal
    else:
        form = ConstanciaForm(initial=initial_data)
    
     # Opcional: mostrar solicitudes pasadas en el mismo dashboard
    solicitudes = Constancia.objects.filter(usuario=user).order_by("-creado_en")

    return render(
        request,
        "users/user/dashboard.html",
        {"form": form, "form_valido": form_valido,
         "solicitudes": solicitudes}
    )

# Gestión de roles (solo para admins)
@login_required
def manage_roles(request):
    if request.user.role != "admin":
        return redirect("home")  # seguridad, no dejar que otro entre
    
    users = CustomUser.objects.all()
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_role = request.POST.get("role")
        try:
            user = CustomUser.objects.get(id=user_id)
            user.role = new_role
            user.save()
        except CustomUser.DoesNotExist:
            pass
        return redirect("manage_roles")

    return render(request, "users/roles/manage_roles.html", {"users": users})