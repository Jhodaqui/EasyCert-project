from django.urls import path
from .views import (
    register_view, login_view, logout_view, home_view,
    activate_account, resend_activation,
    password_reset_request_view, password_reset_confirm_view
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("home/", home_view, name="home"),
    path("activate/<uidb64>/<token>/", activate_account, name="activate"),
    path("resend-activation/", resend_activation, name="resend_activation"),
    path("password-reset/", password_reset_request_view, name="password_reset"),
    path("reset/<uidb64>/<token>/", password_reset_confirm_view, name="password_reset_confirm"),
]
