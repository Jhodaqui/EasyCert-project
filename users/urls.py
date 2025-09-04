from django.urls import path
from .views import (
    register_view, login_view, logout_view, home_view,
    password_reset_request_view, password_reset_confirm_view, admin_dashboard, users_bulk_upload, user_dashboard, staff_dashboard, manage_roles
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
    path("users/bulk-upload/", users_bulk_upload, name="users_bulk_upload"),
    path("staff-dashboard/", staff_dashboard, name="staff_dashboard"),
    path("user-dashboard/", user_dashboard, name="user_dashboard"),
    path("manage-roles/", manage_roles, name="manage_roles"),
]
