from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("upload/<int:user_id>/", views.upload_pdf_view, name="upload_pdf"),
    path("select/<int:user_id>/", views.select_data_view, name="select_data"),
]
