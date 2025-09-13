from django.urls import path
from .views import (
    register_view, login_view, logout_view, home_view,
    password_reset_request_view, password_reset_confirm_view, admin_dashboard, users_bulk_upload, user_dashboard, mostrar_formulario_constancia, user_dashboard_solicitud, staff_dashboard, manage_roles, procesar_constancia, upload_municipios
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("home/", home_view, name="home"),
    path("password-reset/", password_reset_request_view, name="password_reset"),
    path("reset/<uidb64>/<token>/", password_reset_confirm_view, name="password_reset_confirm"),

    # vistas para la gestión de roles y dashboards
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("", users_bulk_upload, name="users_bulk_upload"),
    path("staff-dashboard/", staff_dashboard, name="staff_dashboard"),
    path("user-dashboard/", user_dashboard, name="user_dashboard"),
    path("formulario-constancia/", mostrar_formulario_constancia, name="formulario_constancia"),
    path('procesar-constancia/', procesar_constancia, name='procesar_constancia'),
    path('upload-municipios/', upload_municipios, name='upload_municipios'),

    path("user-dashboard/solicitud/", user_dashboard_solicitud, name="user_dashboard_solicitud"),
    path("manage-roles/", manage_roles, name="manage_roles"),
]
