from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "nombre_completo", "tipo_documento", "numero_documento", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "numero_documento")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("nombre_completo", "tipo_documento", "numero_documento", "documento_pdf")}),
        ("Permisos", {"fields": ("is_active","is_staff","is_superuser","groups","user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email","nombre_completo","tipo_documento","numero_documento","documento_pdf","password1","password2","is_staff","is_active")}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

