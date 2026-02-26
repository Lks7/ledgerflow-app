from django.urls import path

from . import views

urlpatterns = [
    path("", views.journal_list, name="journal_list"),
    path("new", views.journal_new, name="journal_new"),
    path("create", views.journal_create, name="journal_create"),
    path("delete", views.journal_delete, name="journal_delete"),
    path(
        "update-metadata", views.journal_update_metadata, name="journal_update_metadata"
    ),
    path("edit/<str:month>/<str:journal_id>", views.journal_edit, name="journal_edit"),
    path("update", views.journal_update, name="journal_update"),
    path("export/csv", views.journal_export_csv, name="journal_export_csv"),
    path("accounts", views.account_settings, name="account_settings"),
    path("accounts/create", views.account_create, name="account_create"),
    path("accounts/status", views.account_update_status, name="account_update_status"),
    path("accounts/delete", views.account_delete, name="account_delete"),
    path("accounts/update", views.account_update, name="account_update"),
    path("accounts/balance", views.account_set_balance, name="account_set_balance"),
    path("accounts/export/csv", views.account_export_csv, name="account_export_csv"),
    path("logs", views.journal_logs, name="journal_logs"),
    path("tags", views.tag_settings, name="tag_settings"),
    path("tags/rename", views.tag_rename, name="tag_rename"),
    path("tags/delete", views.tag_delete, name="tag_delete"),
    path("categories", views.category_settings, name="category_settings"),
    path("categories/create", views.category_create, name="category_create"),
    path("categories/update", views.category_update, name="category_update"),
    path("categories/delete", views.category_delete, name="category_delete"),
]
