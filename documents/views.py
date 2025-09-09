import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, JsonResponse , HttpResponseBadRequest
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.contrib import messages
from io import BytesIO

from .forms import ContratoUploadForm, ContratoModalForm
from .models import TempExtractedData, UserContractData, Contrato
from users.models import CustomUser
from .utils import extract_key_value_from_pdf, extract_contract_metadata, generate_individual_package
from django.conf import settings

# para pruebas de pdf
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.units import cm


def generar_certificado(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="certificado.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Titulo", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="Subtitulo", fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Texto", fontName="Helvetica", fontSize=11, alignment=TA_JUSTIFY, leading=15))
    styles.add(ParagraphStyle(name="TablaTitulo", fontName="Helvetica-Bold", fontSize=11, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="TablaTexto", fontName="Helvetica", fontSize=11, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Firma", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER, spaceBefore=30))

    elementos = []

    # ---------------- LOGO ----------------
    ruta_logo = os.path.join(settings.BASE_DIR, "static", "img", "logo-sena-verde.jpg")
    try:
        logo = Image(ruta_logo, width=2*cm, height=2*cm)  # tamaño ajustable
        logo.hAlign = "CENTER"

        t_logo = Table([[logo]], colWidths=[6*cm])
        t_logo.hAlign = "CENTER"
        t_logo.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, "black"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elementos.append(t_logo)
        elementos.append(Spacer(1, 15))
    except Exception as e:
        elementos.append(Paragraph(f"[Error cargando logo: {e}]", styles["Texto"]))

    # ---------------- ENCABEZADO ----------------
    encabezado = [[Paragraph("Certificación 079", styles["Titulo"])]]
    t_encabezado = Table(encabezado, colWidths=[15*cm])
    t_encabezado.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_encabezado)
    elementos.append(Spacer(1, 10))

    subtitulo = [[Paragraph("EL SUSCRITO SUBDIRECTOR (E) DEL SERVICIO NACIONAL DE APRENDIZAJE SENA", styles["Subtitulo"])]]
    t_sub = Table(subtitulo, colWidths=[15*cm])
    t_sub.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_sub)

    hace_constar = [[Paragraph("HACE CONSTAR", styles["Subtitulo"])]]
    t_constar = Table(hace_constar, colWidths=[15*cm])
    t_constar.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_constar)
    elementos.append(Spacer(1, 10))

    # ---------------- TEXTO INTRODUCTORIO ----------------
    texto_intro = [[Paragraph(
        """Que el (la) señor(a) <b>JUAN PÉREZ</b> identificado(a) con C.C. No. 123456789 de Popayán celebró con EL SERVICIO NACIONAL DE APRENDIZAJE SENA,
        el contrato de prestación de servicios personales regulados por la Ley 80 de 1993, Ley 1150 de 2007 y Decreto 1082 de 2015, como se describe a continuación:""",
        styles["Texto"]
    )]]
    t_intro = Table(texto_intro, colWidths=[15*cm])
    t_intro.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_intro)
    elementos.append(Spacer(1, 10))

    # ---------------- TABLA DE DATOS ----------------
    data = [
        [Paragraph("Número y Fecha del Contrato:", styles["TablaTitulo"]),
         Paragraph("1234 del 01/02/2025", styles["TablaTexto"])],
        [Paragraph("Objeto:", styles["TablaTitulo"]),
         Paragraph("Prestar los servicios de apoyo financiero y administrativo en el Grupo Intercentros.", styles["TablaTexto"])],
        [Paragraph("Plazo de ejecución:", styles["TablaTitulo"]),
         Paragraph("Del 01/02/2025 al 31/12/2025", styles["TablaTexto"])],
        [Paragraph("Fecha de Inicio:", styles["TablaTitulo"]),
         Paragraph("01/02/2025", styles["TablaTexto"])],
        [Paragraph("Fecha de Terminación:", styles["TablaTitulo"]),
         Paragraph("31/12/2025", styles["TablaTexto"])],
        [Paragraph("Valor:", styles["TablaTitulo"]),
         Paragraph("$27.192.000 (VEINTISIETE MILLONES CIENTO NOVENTA Y DOS MIL PESOS M/CTE)", styles["TablaTexto"])],
        [Paragraph("Obligaciones Específicas:", styles["TablaTitulo"]),
         Paragraph("Apoyar actividades de control financiero, cuentas por pagar, tesorería, y certificaciones.", styles["TablaTexto"])]
    ]
    tabla = Table(data, colWidths=[6*cm, 9*cm])
    tabla.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, "black"),
        ("GRID", (0,0), (-1,-1), 0.5, "grey"),
        ("VALIGN", (0,0), (-1,-1), "TOP")
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 10))

    # ---------------- NOTA FINAL ----------------
    nota = [[Paragraph(
        "Se expide a solicitud del interesado(a), de acuerdo con la información registrada en los sistemas de información con los que cuenta el SENA, a los diez (10) días de febrero de 2025.",
        styles["Texto"]
    )]]
    t_nota = Table(nota, colWidths=[15*cm])
    t_nota.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_nota)
    elementos.append(Spacer(1, 10))

    # ---------------- FIRMA ----------------
    firma = [[Paragraph(
        "DARIO BERNARDO MONTUFAR BLANCO<br/>Subdirector (E) del Centro Agropecuario<br/>Servicio Nacional de Aprendizaje SENA",
        styles["Firma"]
    )]]
    t_firma = Table(firma, colWidths=[15*cm])
    t_firma.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1, "black")]))
    elementos.append(t_firma)

    doc.build(elementos)
    return response

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

@login_required
@require_POST
def contrato_create_modal(request):
    usuario_id = request.POST.get("usuario_id")
    contrato_id = request.POST.get("contrato_id")  # 👈 ahora puede llegar en el form
    usuario = get_object_or_404(CustomUser, id=usuario_id)

    instance = None
    if contrato_id:
        instance = get_object_or_404(Contrato, id=contrato_id, usuario=usuario)

    form = ContratoModalForm(request.POST, request.FILES, instance=instance, initial={"usuario": usuario})
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    archivo = request.FILES.get("archivo")
    try:
        if archivo:
            file_bytes = archivo.read()
            metadata = extract_contract_metadata(BytesIO(file_bytes))
        else:
            file_bytes = None
            metadata = {}

        contrato = form.save(commit=False)
        contrato.usuario = usuario

        # Completar con metadatos del PDF si no están en el form
        contrato.objetivos_especificos = contrato.objetivos_especificos or metadata.get("objetivos_especificos", "")
        contrato.valor_pago = contrato.valor_pago or metadata.get("valor_pago", "")
        contrato.objeto = contrato.objeto or metadata.get("objeto", "")
        contrato.fecha_fin = contrato.fecha_fin or metadata.get("plazo_fecha", "")

        if not contrato.numero_contrato:
            return JsonResponse({"ok": False, "errors": {"numero_contrato": ["Número de contrato requerido."]}}, status=400)

        contrato.save()

        # Si hay archivo, reemplazarlo
        if file_bytes:
            contrato.archivo.save(f"{contrato.numero_contrato}.pdf", ContentFile(file_bytes), save=True)

        # Actualizar tabla
        html_table = render_to_string(
            "documents/partials/contratos_table.html",
            {"contratos": usuario.contratos.order_by('-creado')},
            request=request
        )

        return JsonResponse({
            "ok": True,
            "message": "Contrato guardado correctamente.",
            "table_html": html_table
        })

    except Exception as e:
        return JsonResponse({"ok": False, "errors": {"__all__": [str(e)]}}, status=500)

@csrf_exempt
@require_POST
def prefill_contrato(request):
    try:
        archivo = request.FILES.get("archivo")
        if not archivo:
            return JsonResponse({"ok": False, "error": "No se envió ningún archivo."}, status=400)

        metadata = extract_contract_metadata(archivo)
        return JsonResponse({"ok": True, "metadata": metadata})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

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

# editable contrato
@login_required
def contrato_detail(request, contrato_id):
    contrato = get_object_or_404(Contrato, id=contrato_id)

    try:
        data = {
            "id": contrato.id,
            "numero_contrato": contrato.numero_contrato or "",
            "fecha_inicio": contrato.fecha_inicio or "",
            "fecha_generacion": contrato.fecha_generacion or "",
            "fecha_fin": contrato.fecha_fin or "",
            "valor_pago": contrato.valor_pago or "",
            "objeto": contrato.objeto or "",
            "objetivos_especificos": contrato.objetivos_especificos or "",
        }
        return JsonResponse({"ok": True, "contrato": data})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# Crear certificado individual
@login_required
@require_POST
def generate_individual_documents(request, user_id):
    """
    POST params:
      - selected_ids : (opcional) cadena separada por comas con ids de contratos.
    Si no hay selected_ids, toma TODOS los contratos del usuario.
    Devuelve un ZIP como FileResponse.
    """
    usuario = get_object_or_404(CustomUser, id=user_id)

    selected = request.POST.get("selected_ids", "")
    contratos_qs = Contrato.objects.filter(usuario=usuario)
    if selected:
        ids = [int(x) for x in selected.split(",") if x.strip().isdigit()]
        contratos_qs = contratos_qs.filter(id__in=ids)

    if not contratos_qs.exists():
        return JsonResponse({"ok": False, "error": "No se encontraron contratos para generar."}, status=400)

    # plantilla
    template_path = os.path.join(settings.BASE_DIR, "templates", "base", "boceto para pruebas.docx")
    if not os.path.isfile(template_path):
        return JsonResponse({"ok": False, "error": "Plantilla boceto no encontrada en templates/base/."}, status=500)

    try:
        zip_path = generate_individual_package(usuario, contratos_qs, template_path)
        # devolver zip como respuesta descargable
        response = FileResponse(open(zip_path, "rb"), as_attachment=True, filename=os.path.basename(zip_path))
        return response
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)