from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TempExtractedData, UserContractData
from .utils import extract_key_value_from_pdf # extract_tables_from_pdf
from users.models import CustomUser

# Create your views here.

@login_required
# def upload_pdf_view(request, user_id):
#     usuario = get_object_or_404(CustomUser, id=user_id)

#     if request.method == "POST" and request.FILES.get("pdf_file"):
#         pdf = request.FILES["pdf_file"]
#         data = extract_tables_from_pdf(pdf)

#         # Limpiar datos anteriores
#         TempExtractedData.objects.filter(usuario=usuario).delete()

#         # Guardar cada línea extraída
#         for item in data:
#             TempExtractedData.objects.create(
#                 usuario=usuario,
#                 clave=item["clave"],  # ej: linea_1, linea_2, etc.
#                 valor=item["valor"]   # el texto de esa línea
#             )

#         messages.success(request, " PDF procesado, selecciona los datos a guardar.")
#         return redirect("documents:select_data", user_id=usuario.id)

#     return render(request, "documents/upload_pdf.html", {"usuario": usuario})
def upload_pdf_view(request, user_id):
    usuario = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST" and request.FILES.get("pdf_file"):
        pdf = request.FILES["pdf_file"]
        data = extract_key_value_from_pdf(pdf)

        # Limpiar datos anteriores
        TempExtractedData.objects.filter(usuario=usuario).delete()

        # Guardar secciones extraídas
        for item in data:
            TempExtractedData.objects.create(
                usuario=usuario,
                clave=item["clave"],  # ej: "1.", "2°"
                valor=item["valor"]   # todo el texto del bloque
            )

        messages.success(request, "✅ PDF procesado por secciones.")
        return redirect("documents:select_data", user_id=usuario.id)

    return render(request, "documents/upload_pdf.html", {"usuario": usuario})


@login_required
def select_data_view(request, user_id):
    usuario = get_object_or_404(CustomUser, id=user_id)
    temp_data = TempExtractedData.objects.filter(usuario=usuario)

    if request.method == "POST":
        seleccionados = request.POST.getlist("selected")
        numero_contrato = request.POST.get("numero_contrato")  # manual
        contratista = request.POST.get("contratista")  # manual

        for item in temp_data:
            if str(item.id) in seleccionados:
                UserContractData.objects.update_or_create(
                    usuario=usuario,
                    campo=item.clave,
                    defaults={"valor": item.valor}
                )

        # Guardar manuales directamente en la tabla final
        if numero_contrato:
            UserContractData.objects.update_or_create(
                usuario=usuario, campo="Número de Contrato", defaults={"valor": numero_contrato}
            )
        if contratista:
            UserContractData.objects.update_or_create(
                usuario=usuario, campo="Contratista", defaults={"valor": contratista}
            )

        temp_data.delete()
        messages.success(request, "Datos guardados en la tabla final con los campos manuales incluidos.")
        return redirect("certificates:manual_fields", user_id=usuario.id)

    return render(
        request,
        "documents/select_data.html",
        {"temp_data": temp_data, "usuario": usuario}
    )