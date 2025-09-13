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
from django.contrib.auth import get_user_model
from .utils import crear_carpetas as crear_CarpetasUsuario
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse

from .forms import RegisterForm, LoginForm, ConstanciaForm, BulkUploadForm, MunicipiosUploadForm
import io
import csv
import pandas as pd
from .models import CustomUser, Constancia, municipios, dptos
from datetime import date

# correo 
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Create your views here.

# Registro
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # ya no requiere activación
            user.save()

            crear_CarpetasUsuario(user)  # <-- Esto ya lo tienes, no se toca

            #  --- envío de correo ---
            try:
                subject = "Bienvenido al sistema de certificaciones"
                from_email = settings.EMAIL_HOST_USER
                to_email = [user.email]

                text_content = f"Hola {user.nombres}, tu registro en el sistema de certificaciones fue exitoso."
                html_content = f"""
                    <p>Hola <strong>{user.nombres}</strong>,</p>
                    <p>Tu registro en <strong>el sistema de certificaciones</strong> fue exitoso.</p>
                    <p>Ya puedes iniciar sesión con tu correo y contraseña.</p>
                """

                msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                messages.success(request, "Usuario registrado con éxito. Se envió un correo de bienvenida.")
            except Exception as e:
                logger.error(f"Error enviando correo de bienvenida: {e}")
                messages.warning(request, "Usuario registrado, pero no se pudo enviar el correo de bienvenida.")

            return redirect("login")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = RegisterForm()
    return render(request, "users/register.html", {"form": form})
# fin del correo 

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
            else:
                # Error específico para credenciales incorrectas
                field_errors['general'] = "🔒 Correo electrónico o contraseña incorrectos. Verifica tus credenciales e intenta nuevamente."
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
            message = render_to_string("users/emails/password_reset_email.html", {"user": user, "reset_link": reset_link})
            send_mail(
                subject,
                "Versión de texto plano: copia y pega este enlace para restablecer tu contraseña: " + reset_link,  # respaldo en texto
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=message  # 👈 clave para que el correo se vea con estilos
            )
            messages.success(request, "Se envió un enlace para restablecer la contraseña.")
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

def users_bulk_upload(request):
    if request.method == "POST":
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            file_name = file.name.lower()

            try:
                # 📌 Si es CSV
                if file_name.endswith(".csv"):
                    decoded_file = file.read().decode("utf-8")
                    io_string = io.StringIO(decoded_file)
                    reader = csv.DictReader(io_string)
                    rows = list(reader)

                # 📌 Si es Excel
                elif file_name.endswith(".xls") or file_name.endswith(".xlsx"):
                    df = pd.read_excel(file)
                    rows = df.to_dict(orient="records")

                else:
                    messages.error(request, "Formato de archivo no soportado. Solo se permite CSV o Excel.")
                    return redirect("users_bulk_upload")

                # Procesamos cada fila
                for row in rows:
                    data = {
                        "nombres": row.get("nombres"),
                        "apellidos": row.get("apellidos"),
                        "tipo_documento": row.get("tipo_documento"),
                        "numero_documento": row.get("numero_documento"),
                        "email": row.get("email"),
                        "password1": row.get("password") or "12345",  # por defecto si no viene
                        "password2": row.get("password") or "12345",
                    }

                    user_form = RegisterForm(data)
                    if user_form.is_valid():
                        user = user_form.save()
                        crear_CarpetasUsuario(user)
                    else:
                        messages.error(request, f"Error en {row.get('email')}: {user_form.errors}")

                messages.success(request, "Usuarios cargados correctamente.")
                return redirect("users_bulk_upload")

            except Exception as e:
                messages.error(request, f"Ocurrió un error procesando el archivo: {str(e)}")
                return redirect("users_bulk_upload")

    else:
        form = BulkUploadForm()

    User = get_user_model()
    users = User.objects.exclude(role="admin")  # Evitar mostrar admins
    return render(request, "users/admin/users_bulk_upload.html", {"form": form, "users": users})


def upload_municipios(request):
    if request.method == "POST":
        form = MunicipiosUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']

            # Validar que sea CSV
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "El archivo debe tener extensión .csv")
                return redirect('upload_municipios')

            try:
                data_set = csv_file.read().decode('utf-8')
                io_string = io.StringIO(data_set)
                reader = csv.DictReader(io_string)

                count = 0
                for row in reader:
                    nombre_mpio = row['nombreMpio']
                    id_depto = row['idDepto']
                    nombre_centro = row['nombreCentro'] if row['nombreCentro'] else None

                    # Validar que el departamento exista
                    try:
                        depto = dptos.objects.get(idDepto=id_depto)
                    except dptos.DoesNotExist:
                        messages.error(request, f"El departamento con ID {id_depto} no existe. Línea omitida.")
                        continue

                    # Crear municipio
                    municipios.objects.create(
                        nombreMpio=nombre_mpio,
                        idDepto=depto,
                        nombreCentro=nombre_centro
                    )
                    count += 1

                messages.success(request, f"Se importaron {count} municipios correctamente.")

            except Exception as e:
                messages.error(request, f"Error procesando el archivo: {str(e)}")
                return redirect('users_bulk_upload')

            return redirect('users_bulk_upload')
    else:
        form = MunicipiosUploadForm()

    # Mostrar municipios cargados
    municipios = municipios.objects.select_related('idDepto').all()

    return render(request, 'users_bulk_upload.html', {
        'form': form,
        'municipios': municipios
    })

@login_required
def staff_dashboard(request):
    # Aquí puedes filtrar según permisos/rol
    solicitudes = Constancia.objects.all().order_by("creado_en")
    usuario = CustomUser.objects.get(id=request.user.id)

    return render(request, "users/staff/dashboard.html", {"solicitudes": solicitudes, "usuario": usuario})

@login_required
def user_dashboard(request):
    user = request.user  
    
    solicitudes = Constancia.objects.filter(usuario=user).order_by("-creado_en")

    return render(
        request,
        "users/user/dashboard_home.html",
        {"solicitudes": solicitudes}
    )

@login_required
def mostrar_formulario_constancia(request):
    user = request.user

    initial_data = {
        "nombre_completo": f"{user.nombres} {user.apellidos}",
        "numero_documento": user.numero_documento,
        "tipo_documento": user.tipo_documento,
        "email": user.email,
    }

    form = ConstanciaForm(initial=initial_data)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string(
            "users/partials/form_constancia_partial.html",
            {"form": form},
            request=request
        )
        return JsonResponse({"form_html": html})

    return JsonResponse({"error": "Petición inválida"}, status=400)

@login_required
def procesar_constancia(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user = request.user
        
        initial_data = {
            "nombre_completo": f"{user.nombres} {user.apellidos}",
            "numero_documento": user.numero_documento,
            "tipo_documento": user.tipo_documento,
            "email": user.email,
        }

        form = ConstanciaForm(request.POST, initial=initial_data)
        
        if form.is_valid():
            try:
                Constancia.objects.create(
                    usuario=user,
                    fecha_inicial=date(int(form.cleaned_data["fecha_inicial"]), 1, 1),
                    fecha_final=date(int(form.cleaned_data["fecha_final"]), 1, 1),
                    comentario=form.cleaned_data["comentario"],
                    estado="pendiente"
                )
                
                # Devolver éxito PERO sin recargar la página
                return JsonResponse({
                    'success': True,
                    'message': 'Solicitud de constancia enviada correctamente.'
                })
                
            except Exception as e:
                print(f"Error al guardar: {e}")
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': ['Error al procesar la solicitud']}
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'error': 'Método no permitido'}, status=400)

@login_required
def user_dashboard_solicitud(request):
    user = request.user

    initial_data = {
        "nombre_completo": f"{user.nombres} {user.apellidos}",
        "numero_documento": user.numero_documento,
        "tipo_documento": user.tipo_documento,
        "email": user.email,
    }

    if request.method == "POST":
        form = ConstanciaForm(request.POST, initial=initial_data)
        if form.is_valid():
            Constancia.objects.create(
                usuario=user,
                fecha_inicial=date(int(form.cleaned_data["fecha_inicial"]), 1, 1),
                fecha_final=date(int(form.cleaned_data["fecha_final"]), 1, 1),
                
            )
            messages.success(request, "Solicitud de constancia enviada correctamente.")
            return redirect("user_dashboard")
    else:
        form = ConstanciaForm(initial=initial_data)

    solicitudes = Constancia.objects.filter(usuario=user).order_by("-creado_en")

    return render(
        request,
        "users/user/dashboard.html",
        {"form": form, "solicitudes": solicitudes}
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
