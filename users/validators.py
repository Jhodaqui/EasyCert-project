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

    uploaded_file.open()
    header = uploaded_file.read(2048)
    uploaded_file.seek(0)

    if magic:
        mime = magic.from_buffer(header, mime=True)
        if mime not in ("application/pdf", "application/x-pdf"):
            raise ValidationError("El archivo no parece un PDF (MIME).")
    else:
        if not header.startswith(b"%PDF-"):
            raise ValidationError("El archivo no tiene cabecera PDF válida.")

    try:
        uploaded_file.seek(0)
        PdfReader(uploaded_file)
        uploaded_file.seek(0)
    except Exception:
        uploaded_file.seek(0)
        raise ValidationError("No se pudo leer el PDF. Puede estar corrupto.")
