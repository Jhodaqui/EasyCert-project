import pdfplumber
import PyPDF2
import re


# def extract_tables_from_pdf(pdf_file):
#     """Lee todo el PDF y devuelve un vector con cada línea como item"""
#     data = []
#     pdf_reader = PyPDF2.PdfReader(pdf_file)
#     text = ""
#     for page in pdf_reader.pages:
#         text += page.extract_text() + "\n"

#     # cada línea del PDF será un diccionario clave-valor genérico
#     for i, line in enumerate(text.split("\n")):
#         if line.strip():  # ignoramos líneas vacías
#             data.append({
#                 "clave": f"linea_{i+1}",
#                 "valor": line.strip()
#             })

#     return data

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
