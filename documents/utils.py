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

def extract_sections_from_pdf(pdf_file):
    """
    Extrae secciones numeradas (1., 2., 3. o 1°, 2°, etc.)
    y devuelve lista de dict con clave = numero y valor = texto del bloque
    """
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"

    # vector para guardar bloques
    data = []
    current_section = None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # detectar inicio de sección (ejemplo: "1.", "2.", "3.", "1°", "2°")
        match = re.match(r"^(\d+[\.\°])\s*(.*)", line)
        if match:
            # si ya había una sección previa, guardarla
            if current_section:
                data.append(current_section)

            # iniciar nueva sección
            num = match.group(1)
            contenido = match.group(2)
            current_section = {"clave": num, "valor": contenido}
        else:
            # si estamos dentro de una sección, concatenar el texto
            if current_section:
                current_section["valor"] += " " + line

    # agregar la última sección si quedó abierta
    if current_section:
        data.append(current_section)

    return data
