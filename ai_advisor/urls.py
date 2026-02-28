from django.urls import path

from . import views

urlpatterns = [
    path("advice", views.monthly_advice, name="monthly_advice"),
    path("advice_ui", views.monthly_advice_ui, name="monthly_advice_ui"),
    path("config", views.config_page, name="ai_config"),
]
