from django.urls import path

from .http_views import mcp_http

urlpatterns = [
    path("http", mcp_http, name="mcp_http"),
]
