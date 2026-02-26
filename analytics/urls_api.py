from django.urls import path

from . import views

urlpatterns = [
    path("monthly", views.monthly_summary_api, name="monthly_summary_api"),
    path("yearly", views.yearly_summary_api, name="yearly_summary_api"),
]
