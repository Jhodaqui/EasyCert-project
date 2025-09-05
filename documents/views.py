from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TempExtractedData, UserContractData
from .utils import extract_key_value_from_pdf # extract_tables_from_pdf
from users.models import CustomUser

# importaciones de pruebas


# Create your views here.

@login_required
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


# vista de prueba
import io
from io import BytesIO
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile

from .forms import ContratoModalForm
from .models import Contrato, TempExtractedData, UserContractData
from users.models import CustomUser  # ajusta si tu ruta/nombre es distinto
from .utils import extract_key_value_from_pdf, extract_contract_metadata

@login_required
@require_POST
def contrato_create_modal(request):
    """
    Vista que maneja el POST desde el modal:
    1. Valida el formulario
    2. Extrae datos del PDF y guarda respaldo en TempExtractedData / UserContractData
    3. Extrae metadata (objeto, obligaciones, objetivos, valor_pago, etc.)
    4. Crea el contrato principal y asocia archivo
    5. Devuelve JSON con tabla actualizada
    """
    usuario_id = request.POST.get("usuario_id")
    usuario = get_object_or_404(CustomUser, id=usuario_id)

    # ---------- (1) Validar formulario ----------
    form = ContratoModalForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    uploaded = request.FILES.get("archivo")
    if not uploaded:
        return JsonResponse({"ok": False, "errors": {"archivo": ["Archivo PDF requerido."]}}, status=400)

    try:
        # Leemos bytes del archivo (para usar varias veces)
        file_bytes = uploaded.read()
        pdf_stream = BytesIO(file_bytes)

        # ---------- (2) Respaldo en tablas temporales ----------
        items = extract_key_value_from_pdf(BytesIO(file_bytes))
        TempExtractedData.objects.filter(usuario=usuario).delete()

        for it in items:
            # Guardar en tabla temporal
            TempExtractedData.objects.create(
                usuario=usuario,
                clave=it.get("clave"),
                valor=it.get("valor")
            )
            # Guardar también en tabla final de respaldo
            UserContractData.objects.update_or_create(
                usuario=usuario,
                campo=it.get("clave"),
                defaults={"valor": it.get("valor")}
            )

        # ---------- (3) Extraer metadata clave ----------
        metadata = extract_contract_metadata(BytesIO(file_bytes))
        objeto = metadata.get("objeto", "")
        obligaciones = metadata.get("obligaciones", "")
        objetivos = metadata.get("objetivos_especificos", "")
        valor_pago = metadata.get("valor_pago", "")
        plazo_fecha = metadata.get("plazo_fecha")

        # También intentar detectar "OBLIGACIONES ESPECÍFICAS" de los items
        obligaciones_extra = "\n".join(
            [it["valor"] for it in items if "OBLIGACIONES ESPECÍFICAS" in it.get("clave", "").upper()]
        )
        if obligaciones_extra:
            obligaciones = f"{obligaciones}\n{obligaciones_extra}".strip()

        # ---------- (4) Crear contrato principal ----------
        contrato = form.save(commit=False)
        contrato.usuario = usuario
        contrato.objeto = objeto
        contrato.obligaciones = obligaciones
        contrato.objetivos_especificos = objetivos
        contrato.fecha_fin = plazo_fecha

        # Si no viene en el form, usar el detectado
        if not contrato.valor_pago:
            contrato.valor_pago = valor_pago or ""

        contrato.save()
        contrato.archivo.save(uploaded.name, ContentFile(file_bytes), save=True)

        # ---------- (5) Guardar en respaldo UserContractData ----------
        if contrato.numero_contrato:
            UserContractData.objects.update_or_create(
                usuario=usuario,
                campo="Número de Contrato",
                defaults={"valor": contrato.numero_contrato}
            )
        if contrato.valor_pago:
            UserContractData.objects.update_or_create(
                usuario=usuario,
                campo="Valor de Pago",
                defaults={"valor": contrato.valor_pago}
            )

        # ---------- (6) Renderizar tabla de contratos actualizada ----------
        html_table = render_to_string("documents/partials/contratos_table.html", {
            "contratos": usuario.contratos.order_by('-creado')
        }, request=request)

        return JsonResponse({
            "ok": True,
            "message": "Contrato guardado correctamente.",
            "table_html": html_table
        })

    except Exception as e:
        return JsonResponse({"ok": False, "errors": {"__all__": [str(e)]}}, status=500)


@login_required
def contratos_usuario_view(request, user_id):
    usuario = get_object_or_404(CustomUser, id=user_id)
    contratos = usuario.contratos.all()

    html = render_to_string(
        "documents/partials/contratos_table.html",
        {"contratos": contratos},
        request=request
    )

    return JsonResponse({"html": html})

from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt  # si usas fetch directo, si no podemos manejarlo con CSRF token
def prefill_contrato_from_pdf(request):
    if request.method == "POST" and request.FILES.get("archivo"):
        pdf_file = request.FILES["archivo"]
        try:
            metadata = extract_contract_metadata(pdf_file)
            return JsonResponse({"ok": True, "metadata": metadata})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
    return JsonResponse({"ok": False, "error": "No se envió archivo"}, status=400)
