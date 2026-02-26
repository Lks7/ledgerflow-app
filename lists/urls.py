from django.urls import path

from . import views

urlpatterns = [
    path("", views.shopping_list, name="shopping_list"),
    path("create", views.shopping_create, name="shopping_create"),
    path("update", views.shopping_update, name="shopping_update"),
    path("status", views.shopping_update_status, name="shopping_update_status"),
    path("delete", views.shopping_delete, name="shopping_delete"),
    path("ai-analyze", views.ai_analyze, name="shopping_ai_analyze"),
    path("to-journal-draft", views.to_journal_draft, name="to_journal_draft"),
]
