import os 
import zipfile
from io import BytesIO
from django.conf import settings
import pandas as pd
from mailmerge import MailMerge
from django.utils.text import slugify
import pdfplumber
import re
from datetime import date

SPANISH_MONTHS = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
    "noviembre":11,"diciembre":12
}

def _parse_spanish_date(text):
    if not text:
        return None
    t = text.strip().lower()
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})', t, re.I)
    if m:
        try:
            return date(int(m.group(3)), SPANISH_MONTHS[m.group(2)], int(m.group(1)))
        except:
            return None
    m2 = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})', t)
    if m2:
        y = int(m2.group(3))
        if y < 100: y += 2000
        try:
            return date(y, int(m2.group(2)), int(m2.group(1)))
        except:
            return None
    return None

def _extract_value_amount(text):
    if not text:
        return None
    m = re.search(r'\$\s*[\d\.,]+', text)
    if m:
        return m.group(0).strip()
    m2 = re.search(r'\(\s*\$?\s*[\d\.,]+\s*\)', text)
    if m2:
        return m2.group(0).strip("()").strip()
    return None

def _amount_to_digits(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^\d]', '', text) or ""

def _format_amount(valor_num: str) -> str:
    """Formatea con puntos de miles: 2472000 -> 2.472.000"""
    try:
        n = int(valor_num)
        return f"{n:,}".replace(",", ".")
    except:
        return valor_num

def _clean_plazo_text(text):
    """Extrae solo la fecha del plazo en formato 'DD DE MES DE YYYY'."""
    if not text:
        return ""

    m = re.search(r"\d{1,2}\s+DE\s+[A-ZÁÉÍÓÚÑ]+\s+DE\s+\d{4}", text, re.I)
    if m:
        return m.group(0).strip()

    return text.strip()

def extract_key_value_from_pdf(pdf_file):
    out = []
    with pdfplumber.open(pdf_file) as pdf:
        full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)

        # ===== OBJETO =====
        match_objeto = re.search(
            r"OBJETO[:\s]*(.*?)(EDUCACI[oÓ]N\s+Y/O\s+FORMACI[oÓ]N|VALOR|PLAZO|$)",
            full_text, re.I | re.S
        )
        if match_objeto:
            objeto_text = match_objeto.group(1).strip()
            out.append({"clave": "Objeto", "valor": objeto_text})

        # ===== VALOR =====
        match_valor = re.search(
            r"VALOR\s+Y\s+FORMA\s+DE\s+PAGO[:\s]*(.*?)(PLAZO|LUGAR|SUPERVISOR|$)",
            full_text, re.I | re.S
        )
        if match_valor:
            valor_text = match_valor.group(1).strip()
            valor_num = _amount_to_digits(_extract_value_amount(valor_text) or valor_text)
            if valor_num:
                valor_fmt = f"{int(valor_num):,}".replace(",", ".")
                out.append({"clave": "Valor de Pago", "valor": valor_fmt})

        # ===== PLAZO (solo fecha limpia) =====
        match_plazo = re.search(
            r"PLAZO[:\s]*(.*?)(LUGAR|SUPERVISOR|ORDENADOR|$)",
            full_text, re.I | re.S
        )
        if match_plazo:
            plazo_text = _clean_plazo_text(match_plazo.group(1))
            if plazo_text:
                out.append({"clave": "Plazo", "valor": plazo_text})

        # ===== OBJETIVOS ESPECÍFICOS =====
        match_objetivos = re.search(
            r"(OBJETIVOS\s+ESPEC[IÍ]FICOS|OBLIGACIONES\s+ESPEC[IÍ]FICAS)[:\s]*(.*?)(PAR[ÁA]GRAFO|OBLIGACIONES\s+DEL|IDENTIFICACI[oó]N|$)",
            full_text, re.S | re.I
        )
        if match_objetivos:
            objetivos_text = match_objetivos.group(2).strip()
            out.append({"clave": "Objetivos Específicos", "valor": objetivos_text})

    return out

def extract_contract_metadata(pdf_file):
    items = extract_key_value_from_pdf(pdf_file)

    metadata = {
        "objeto": "",
        "valor_pago": "",
        "valor_pago_raw": "",
        "plazo_fecha": "",
        "objetivos_especificos": "",
    }

    for it in items:
        k = (it["clave"] or "").lower()
        if "objeto" in k:
            metadata["objeto"] = it["valor"]
        elif "valor" in k:
            metadata["valor_pago"] = it["valor"]      # 2.472.000
            metadata["valor_pago_raw"] = it.get("raw", "")  # 2472000
        elif "plazo" in k:
            metadata["plazo_fecha"] = it["valor"]
        elif "objetivo" in k:
            metadata["objetivos_especificos"] = it["valor"]

    return metadata

#prueba de mailmerge
def _safe_filename(s: str) -> str:
    if not s:
        return "sin_numero"
    return slugify(s)[:120]

def generate_individual_package(usuario, contratos_qs, template_docx_path):
    """
    Genera:
      - Un ZIP con todos los .docx generados + el Excel
      - Se guarda únicamente el ZIP en media/usuarios/<documento>/individual/
    🔑 El Excel y los DOCX son temporales y se eliminan después.
    """
    import tempfile
    import shutil

    # carpeta destino
    base_folder = os.path.join(settings.MEDIA_ROOT, "usuarios", usuario.numero_documento, "individual")
    os.makedirs(base_folder, exist_ok=True)

    # --- Carpeta temporal ---
    temp_dir = tempfile.mkdtemp()

    # --- Excel temporal ---
    rows = []
    for c in contratos_qs:
        rows.append({
            "NUMERO_CONTRATO": c.numero_contrato or "",
            "FECHA_GENERACION": c.fecha_generacion or "",
            "FECHA_INICIO": c.fecha_inicio or "",
            "FECHA_FIN": c.fecha_fin or "",
            "VALOR_PAGO": c.valor_pago or "",
            "OBJETO": c.objeto or "",
            "OBJETIVOS_ESPECIFICOS": c.objetivos_especificos or "",
            "CONTRATO_ID": c.id,
            "NOMBRES": usuario.nombres,
            "APELLIDOS": usuario.apellidos,
            "TIPO_DOCUMENTO": usuario.get_tipo_documento_display_full(),
            "NUMERO_DOCUMENTO": usuario.numero_documento,
            "EMAIL": usuario.email,
        })
    df = pd.DataFrame(rows)
    excel_path = os.path.join(temp_dir, "contratos.xlsx")
    df.to_excel(excel_path, index=False, engine="openpyxl")

    # --- DOCX temporales ---
    doc_paths = []
    for row in rows:
        nro = row.get("NUMERO_CONTRATO") or f"id{row.get('CONTRATO_ID')}"
        out_name = f"{_safe_filename(nro)}.docx"
        out_path = os.path.join(temp_dir, out_name)

        try:
            with MailMerge(template_docx_path) as m:
                safe_row = {k: (v if v is not None else "") for k, v in row.items()}
                safe_row.pop("CONTRATO_ID", None)
                m.merge(**safe_row)
                m.write(out_path)
        except Exception:
            shutil.copy(template_docx_path, out_path)

        doc_paths.append(out_path)

    # --- Crear ZIP (único archivo persistente) ---
    zip_name = f"contratos_{usuario.numero_documento}.zip"
    zip_path = os.path.join(base_folder, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(excel_path, arcname="contratos.xlsx")
        for p in doc_paths:
            zf.write(p, arcname=os.path.basename(p))

    # 🧹 limpiar temporales (Excel + DOCX)
    shutil.rmtree(temp_dir, ignore_errors=True)

    return zip_path

