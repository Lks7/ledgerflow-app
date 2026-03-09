from django.urls import path

from . import views

urlpatterns = [
    path("advice", views.monthly_advice, name="monthly_advice"),
    path("advice_ui", views.monthly_advice_ui, name="monthly_advice_ui"),
    path("reconcile/form", views.reconcile_form, name="reconcile_form"),
    path("reconcile/preview", views.reconcile_preview, name="reconcile_preview"),
    path("reconcile/commit", views.reconcile_commit, name="reconcile_commit"),
    path("config", views.config_page, name="ai_config"),
]
