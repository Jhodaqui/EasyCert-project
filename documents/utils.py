import pdfplumber

def extract_tables_from_pdf(pdf_file):
    """
    Procesa el PDF y devuelve lista de diccionarios con clave → valor
    """
    extracted = []

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # Tablas
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 2:
                        clave = str(row[0]).strip()
                        valor = str(row[1]).strip()
                        extracted.append({"clave": clave, "valor": valor})

            # Texto línea a línea (opcional)
            text = page.extract_text()
            if text:
                for i, line in enumerate(text.split("\n")):
                    extracted.append({"clave": f"Línea {i+1}", "valor": line.strip()})

    return extracted
