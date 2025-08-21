from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm

# Create your views here.

# registro
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro exitoso.")
            return redirect("home")
        else:
            messages.error(request, "Hay errores en el formulario.")
    else:
        form = RegisterForm()
    return render(request, "users/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)  # USERNAME_FIELD = 'email'
            if user:
                login(request, user)
                return redirect("home")
            messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = LoginForm()
    return render(request, "users/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def home_view(request):
    return render(request, "home.html")