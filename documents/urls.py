from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("upload/<int:user_id>/", views.upload_pdf_view, name="upload_pdf"),
    path("select/<int:user_id>/", views.select_data_view, name="select_data"),
    path("contrato/create-modal/", views.contrato_create_modal, name="contrato_create_modal"),
    path("contratos/<int:user_id>/", views.contratos_usuario_view, name="contratos_usuario"),
    path("contrato/prefill/", views.prefill_contrato, name="prefill_contrato"),
    path("contrato/<int:contrato_id>/", views.contrato_detail, name="contrato_detail"),
    path("generate-individual/<int:user_id>/", views.generate_individual_documents, name="generate_individual"),
]
