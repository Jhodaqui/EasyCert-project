import pdfplumber
import PyPDF2
import re

# importaciones de pruebas
from datetime import date, datetime
from io import BytesIO

def extract_key_value_from_pdf(pdf_file):
    """
    Extrae pares (clave, valor) desde tablas de dos columnas del PDF.
    Maneja el caso especial de 'Obligaciones Específicas', uniendo todos los numerales en un solo bloque.
    """

    def _cleanup_key(k: str) -> str:
        k = (k or "").strip()
        k = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", k)  # quita "2. " al inicio
        k = k.replace("：", ":")
        k = k.rstrip(":")
        k = re.sub(r"\s+", " ", k)
        return k

    def _flush(current_key, buffer, out):
        if current_key and buffer:
            text = " ".join(x for x in buffer if x).strip()
            if re.search(r"obligaciones\s+espec[ií]ficas", current_key, re.I):
                text = _process_obligaciones(text)
            if text:
                out.append({"clave": _cleanup_key(current_key), "valor": text})

    def _process_obligaciones(text: str) -> str:
        """
        Une las obligaciones numeradas en un solo bloque.
        Corta antes de 'PARÁGRAFO'.
        """
        up = text.upper()
        idx = up.find("PARÁGRAFO")
        if idx != -1:
            text = text[:idx].strip()

        # Detectar numerales con regex: "1.", "2)", "3°"
        partes = re.split(r"(?=\s*\d+[\.\)\°])", text)
        partes = [p.strip() for p in partes if p.strip()]

        return " ".join(partes)

    out = []
    with pdfplumber.open(pdf_file) as pdf:
        found_table = False
        for page in pdf.pages:
            tables = page.extract_tables() or []
            if tables:
                found_table = True
            current_key = None
            buffer = []

            for table in tables:
                for row in table:
                    if not row:
                        continue
                    cells = [(c or "").strip() for c in row]
                    left = cells[0] if len(cells) > 0 else ""
                    right = " ".join(cells[1:]).strip() if len(cells) > 1 else ""

                    if left:
                        _flush(current_key, buffer, out)
                        current_key = left
                        buffer = []
                        if right:
                            buffer.append(right)
                    else:
                        if current_key and right:
                            buffer.append(right)
            _flush(current_key, buffer, out)

        # fallback si no hay tablas
        if not found_table:
            full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            current_key = None
            buffer = []
            for line in lines:
                m = re.match(r"^(\d+\s*[\.\)]\s*)?([A-ZÁÉÍÓÚÑ0-9][^:]{2,}):\s*(.*)$", line)
                if m:
                    _flush(current_key, buffer, out)
                    current_key = m.group(2)
                    rest = (m.group(3) or "").strip()
                    buffer = []
                    if rest:
                        buffer.append(rest)
                else:
                    if current_key:
                        buffer.append(line)
            _flush(current_key, buffer, out)

        # --- Obligaciones Específicas aunque haya tablas ---
        full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        match = re.search(
            r"Obligaciones\s+Espec[ií]ficas:(.*?)(PARÁGRAFO|OBLIGACIONES DEL SENA|$)",
            full_text, re.S | re.I
        )
        if match:
            obligaciones_raw = match.group(1).strip()
            obligaciones_final = _process_obligaciones(obligaciones_raw)
            out.append({
                "clave": "Obligaciones Específicas",
                "valor": obligaciones_final
            })

    # merge duplicados
    merged = []
    idx_by_key = {}
    for item in out:
        k = item["clave"]
        if k in idx_by_key:
            merged[idx_by_key[k]]["valor"] += " " + item["valor"]
        else:
            idx_by_key[k] = len(merged)
            merged.append(item)

    return merged

# Funciones de pruebas
SPANISH_MONTHS = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12
}

def _parse_spanish_date(text):
    if not text:
        return None
    t = text.strip().lower()
    # formato "31 de diciembre de 2025"
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+de\s+(\d{4})', t, re.I)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month = SPANISH_MONTHS.get(month_name)
        if month:
            try:
                return date(year, month, day)
            except Exception:
                return None
    # formato dd/mm/yyyy  o dd-mm-yyyy
    m2 = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})', t)
    if m2:
        d = int(m2.group(1)); mo = int(m2.group(2)); y = int(m2.group(3))
        if y < 100: y += 2000
        try:
            return date(y, mo, d)
        except:
            return None
    # último recurso: buscar 4 dígitos como año y devolver 31/12/<año> (poco ideal)
    m3 = re.search(r'(\d{4})', t)
    if m3:
        try:
            return date(int(m3.group(1)), 12, 31)
        except:
            return None
    return None

def _extract_value_amount(text):
    """Intenta capturar un monto monetario en formato $xx.xxx.xxx o similar o en paréntesis ($xx.xxx)"""
    if not text:
        return None
    # buscar $... más cercano
    m = re.search(r'\$\s*[\d\.,]+', text)
    if m:
        return m.group(0).strip()
    # buscar paréntesis con $ dentro
    m2 = re.search(r'\(\s*\$?\s*[\d\.,]+\s*\)', text)
    if m2:
        return m2.group(0).strip().strip("()")
    # buscar texto en mayúsculas con la palabra "VEINTI" u "UN MILLÓN" -> devolver el bloque
    m3 = re.search(r'SE\s*FIJA\s*.*?VALOR\s*(.*?)(PLAZO|LUGAR|SUPERVISOR|$)', text, re.I | re.S)
    if m3:
        return m3.group(1).strip()
    return None

def extract_contract_metadata(pdf_file):
    """
    Recibe un archivo (file-like: BytesIO o UploadedFile).
    Devuelve dict: objeto, obligaciones, objetivos_especificos, plazo_fecha (date|None), valor_pago (str|None)
    """
    # Asegurarnos de trabajar con BytesIO
    if not hasattr(pdf_file, "read"):
        raise ValueError("pdf_file debe ser file-like.")
    b = pdf_file.read()
    stream = BytesIO(b)

    # Texto completo
    import pdfplumber
    text_full = ""
    try:
        with pdfplumber.open(stream) as pdf:
            for p in pdf.pages:
                page_text = p.extract_text() or ""
                text_full += page_text + "\n"
    except Exception:
        # fallback si pdfplumber falla
        try:
            from PyPDF2 import PdfReader
            stream.seek(0)
            reader = PdfReader(stream)
            for p in reader.pages:
                text_full += (p.extract_text() or "") + "\n"
        except Exception:
            text_full = ""

    # Normalizar
    norm = re.sub(r'\s+', ' ', text_full).strip()

    # OBJETO
    objeto = None
    m_obj = re.search(r'OBJETO\s*[:\-]\s*(.+?)(VALOR Y FORMA DE PAGO|PLAZO|LUGAR DE EJECUCIÓN|LUGAR DE EJECUCI[oó]N|SUPERVISOR|EXPERIENCIA|$)', text_full, re.I|re.S)
    if m_obj:
        objeto = m_obj.group(1).strip()

    # VALOR/PAGO
    valor_pago = None
    m_val = re.search(r'VALOR\s+Y\s+FORMA\s+DE\s+PAGO\s*[:\-]\s*(.+?)(PLAZO|LUGAR DE EJECUCIÓN|SUPERVISOR|$)', text_full, re.I|re.S)
    if m_val:
        valor_pago = _extract_value_amount(m_val.group(1))
    if not valor_pago:
        valor_pago = _extract_value_amount(text_full)

    # PLAZO (buscamos el bloque "PLAZO: ...")
    plazo_fecha = None
    m_plazo = re.search(r'PLAZO\s*[:\-]\s*([^\n\r]+)', text_full, re.I)
    if m_plazo:
        fecha_text = m_plazo.group(1).strip()
        plazo_fecha = _parse_spanish_date(fecha_text)
    if not plazo_fecha:
        # buscar fechas en todo el texto e intentar tomar la más "final"
        fechas = re.findall(r'\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', text_full, re.I)
        for f in reversed(fechas):
            d = _parse_spanish_date(f)
            if d:
                plazo_fecha = d
                break

    # OBLIGACIONES ESPECÍFICAS
    obligaciones = None
    m_obl = re.search(r'2\.\s*Obligaciones\s+Espec[ií]ficas[:\-]\s*(.+?)(PAR[AÁ]GRAFO|OBLIGACIONES DEL SENA|3\.|IDENTIFICACI[oó]N|$)', text_full, re.I|re.S)
    if not m_obl:
        m_obl = re.search(r'Obligaciones\s+Espec[ií]ficas[:\-]\s*(.+?)(PAR[AÁ]GRAFO|OBLIGACIONES DEL SENA|3\.|IDENTIFICACI[oó]N|$)', text_full, re.I|re.S)
    if m_obl:
        obligaciones = m_obl.group(1).strip()
    # Si no se encontró, también intentamos usar tu extractor de tablas y buscar la clave "Obligaciones Específicas"
    if not obligaciones:
        try:
            # mover stream a inicio y usar extract_key_value_from_pdf si está definida
            stream2 = BytesIO(b)
            from .utils import extract_key_value_from_pdf as _old_extractor
            items = _old_extractor(stream2)
            for it in items:
                clave = (it.get("clave") or "").lower()
                if "obligac" in clave:
                    obligaciones = (obligaciones or "") + " " + it.get("valor","")
        except Exception:
            pass

    # OBJETIVOS ESPECÍFICOS (si existe un bloque explícito)
    objetivos = None
    m_objesp = re.search(r'OBJETIVOS\s+ESPEC[ií]FICOS?[:\-]\s*(.+?)(PAR[AÁ]GRAFO|OBLIGACIONES|IDENTIFICACI[oó]N|$)', text_full, re.I|re.S)
    if m_objesp:
        objetivos = m_objesp.group(1).strip()

    return {
        "objeto": objeto or "",
        "valor_pago": valor_pago or "",
        "plazo_fecha": plazo_fecha,
        "obligaciones": obligaciones or "",
        "objetivos_especificos": objetivos or ""
    }