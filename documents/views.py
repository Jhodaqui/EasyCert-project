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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# Definir tamaño carta (Letter)
LETTER = (612, 792)  # 21,59cm x 27,94cm

def generar_certificado(request):
    usuario = get_object_or_404(CustomUser, id=103)  # Usuario de prueba
    contrato = get_object_or_404(Contrato, id=25, usuario=usuario)  # Contrato de prueba
    
    # Fuente Calibri
    ruta_fuente = os.path.join(settings.BASE_DIR, "static", "fonts", "calibri.ttf")
    pdfmetrics.registerFont(TTFont("Calibri", ruta_fuente))

        # Registrar fuentes Calibri
    ruta_fuente = os.path.join(settings.BASE_DIR, "static", "fonts")
    pdfmetrics.registerFont(TTFont("Calibri", os.path.join(ruta_fuente, "calibri.ttf")))
    pdfmetrics.registerFont(TTFont("Calibri-Bold", os.path.join(ruta_fuente, "calibrib.ttf")))
    pdfmetrics.registerFont(TTFont("Calibri-Italic", os.path.join(ruta_fuente, "calibrii.ttf")))
    pdfmetrics.registerFont(TTFont("Calibri-BoldItalic", os.path.join(ruta_fuente, "calibriz.ttf")))
    
    tituloInicial = "<b>EL SUSCRITO SUBDIRECTOR (E) DEL SERVICIO NACIONAL DE APRENDIZAJE SENA</b>"
    introduccion = f"""Que el (la) señor(a) {usuario.nombres} {usuario.apellidos} identificado(a) con 
    {usuario.tipo_documento} No. {usuario.numero_documento} de Popayán celebró con EL SERVICIO NACIONAL DE APRENDIZAJE SENA, 
    el (los) siguiente(s) contrato(s) de prestación de servicios personales regulados por la Ley 80 de 1993, 
    Ley 1150 de 2007 y Decreto 1082 de 2015, como se describe a continuación:"""
    
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="certificado.pdf"'

    # Documento Letter con márgenes definidos
    doc = SimpleDocTemplate(response, pagesize=LETTER,
                            leftMargin=3*cm, rightMargin=3*cm,
                            topMargin=3*cm, bottomMargin=2.5*cm)

    # Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Certificacion", fontName="Calibri-Italic", fontSize=11,
                              alignment=TA_LEFT, spaceAfter=15))
    styles.add(ParagraphStyle(name="SubtituloCalibri", fontName="Calibri-Bold", fontSize=14,
                              alignment=TA_CENTER, spaceAfter=12, leading=16))
    styles.add(ParagraphStyle(name="IntroCalibri", fontName="Calibri", fontSize=11,
                              alignment=TA_JUSTIFY, leading=15))
    styles.add(ParagraphStyle(name="TablaTitulo", fontName="Calibri-Bold", fontSize=11,
                              alignment=TA_LEFT, spaceAfter=3, leading=13))
    styles.add(ParagraphStyle(name="TablaTexto", fontName="Calibri", fontSize=11,
                              alignment=TA_LEFT, leading=13))
    styles.add(ParagraphStyle(name="FirmaPrincipal", fontName="Calibri", fontSize=11,
                              alignment=TA_LEFT, leading=14))
    styles.add(ParagraphStyle(name="FirmaSecundaria", fontName="Calibri", fontSize=10,
                              alignment=TA_LEFT, leading=12))

    elementos = []

    # ---------------- SUBTÍTULOS ----------------
    elementos.append(Paragraph(
        tituloInicial,
        styles["SubtituloCalibri"]))
    elementos.append(Paragraph("<b>HACE CONSTAR</b>", styles["SubtituloCalibri"]))
    elementos.append(Spacer(1, 15))

    # ---------------- INTRO ----------------
    intro = introduccion
    elementos.append(Paragraph(intro, styles["IntroCalibri"]))
    elementos.append(Spacer(1, 15))

    # ---------------- TABLA DE DATOS ----------------
    data = [
        [Paragraph("Número y Fecha del Contrato:", styles["TablaTitulo"]),
         Paragraph( f"{contrato.numero_contrato} del {contrato.fecha_generacion}", styles["TablaTexto"])],
        [Paragraph("Objeto:", styles["TablaTitulo"]),
         Paragraph(f"{contrato.objeto}", styles["TablaTexto"])],
        [Paragraph("Plazo de ejecución:", styles["TablaTitulo"]),
         Paragraph(f"{contrato.fecha_inicio} al {contrato.fecha_fin}", styles["TablaTexto"])],
        [Paragraph("Fecha de Inicio de Ejecución:", styles["TablaTitulo"]),
         Paragraph(f"{contrato.fecha_inicio}", styles["TablaTexto"])],
        [Paragraph("Fecha de Terminación del Contrato:", styles["TablaTitulo"]),
         Paragraph(f"{contrato.fecha_fin}", styles["TablaTexto"])],
        [Paragraph("Valor:", styles["TablaTitulo"]),
         Paragraph(f"El valor del contrato para todos los efectos legales y fiscales, se fijó en la suma de ${contrato.valor_pago} (cuantía del contrato)", styles["TablaTexto"])],
        [Paragraph("Obligaciones Específicas:", styles["TablaTitulo"]),
         Paragraph(f"""{contrato.objetivos_especificos}""", styles["TablaTexto"])]
    ]
    tabla = Table(data, colWidths=[6*cm, (LETTER[0] - 6*cm - 6*cm)])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 15))

    # ---------------- EXPEDICIÓN ----------------
    expedicion = """Se expide a solicitud del interesado(a), de acuerdo con la información registrada en los sistemas de información con los que cuenta el SENA, a los diez (10) días de febrero de 2025."""
    elementos.append(Paragraph(expedicion, styles["IntroCalibri"]))
    elementos.append(Spacer(1, 30))

    # ---------------- FIRMAS ----------------
    firmas = []

    # Firma del Subdirector
    firma_subdirector = Paragraph(
        """___________________________<br/>
        <b>DARIO BERNARDO MONTUFAR BLANCO</b><br/>
        Subdirector (E) del Centro Agropecuario<br/>
        Servicio Nacional de Aprendizaje SENA""",
        styles["FirmaPrincipal"]
    )

    # Firma Proyecto
    firma_proyecto = Paragraph(
        """Proyecto: Danna Isabela Ordoñez Navia<br/>
        Cargo: Apoyo Financiero y Administrativo Grupo Intercentros""",
        styles["FirmaSecundaria"]
    )

    # Firma Revisó
    firma_reviso = Paragraph(
        """Revisó: Ariel Pabón<br/>
        Cargo: Coordinador Administrativo y Financiero Intercentros""",
        styles["FirmaSecundaria"]
    )

    # Organizamos en tabla
    tabla_firmas = Table(
        [
            [firma_subdirector],   # primera fila (subdirector)
            [Spacer(1, 20)],       # espacio
            [firma_proyecto],      # segunda fila (proyecto)
            [Spacer(1, 10)],       # espacio
            [firma_reviso]         # tercera fila (revisó)
        ],
        colWidths=[LETTER[0] - 9*cm]  # ocupa espacio más hacia la derecha
    )

    tabla_firmas.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "RIGHT"),   # alinea a la derecha
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))

    elementos.append(Spacer(1, 40))
    elementos.append(tabla_firmas)

    # ---------------- ENCABEZADO Y PIE ----------------
    def header_footer(canvas, doc):
        canvas.saveState()
        # Logo centrado
        ruta_logo = os.path.join(settings.BASE_DIR, "static", "img", "logo-sena-verde.jpg")
        logo = ImageReader(ruta_logo)
        canvas.drawImage(logo, LETTER[0]/2 - 25, LETTER[1]-70, width=50, height=50, preserveAspectRatio=True)

        # Certificación
        canvas.setFont("Calibri-Italic", 11)
        canvas.drawString(3*cm, LETTER[1]-60, "Certificación No. 001")

        # Pie de página
        footer_text = "Regional Cauca / Centro de Formación Agropecuario - Carrera 9ª 71N–60 B/ El Placer, Popayán – Cauca. PBX 57 602 8247678 Ext:2224"
        canvas.setFont("Calibri", 9)
        canvas.drawCentredString(LETTER[0] / 2.0, 1.56*cm, footer_text)

        canvas.restoreState()

    doc.build(elementos, onFirstPage=header_footer, onLaterPages=header_footer)

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