from django.core.exceptions import ValidationError
from PyPDF2 import PdfReader
try:
    import magic
except Exception:
    magic = None

MAX_PDF_SIZE_MB = 2

def validate_pdf(uploaded_file):
    # tamaño
    if uploaded_file.size > MAX_PDF_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"El PDF supera {MAX_PDF_SIZE_MB} MB.")

    # MIME real (si python-magic está disponible)
    if magic:
        mime = magic.from_buffer(uploaded_file.read(2048), mime=True)
        uploaded_file.seek(0)
        if mime not in ("application/pdf", "application/x-pdf"):
            raise ValidationError("El archivo no es un PDF (MIME).")
    else:
        # simple check header
        header = uploaded_file.read(5)
        uploaded_file.seek(0)
        if header != b"%PDF-":
            raise ValidationError("El archivo no tiene cabecera PDF válida.")

    # intentar leer con PyPDF2
    try:
        reader = PdfReader(uploaded_file)
        _ = len(reader.pages)
        uploaded_file.seek(0)
    except Exception:
        uploaded_file.seek(0)
        raise ValidationError("No se pudo leer el PDF. Verifica que no esté corrupto.")