from django.urls import path

from . import views

urlpatterns = [
    path("", views.todo_list, name="todo_list"),
    path("create", views.todo_create, name="todo_create"),
    path("update", views.todo_update, name="todo_update"),
    path("toggle", views.todo_toggle, name="todo_toggle"),
    path("delete", views.todo_delete, name="todo_delete"),
    path("move", views.todo_move, name="todo_move"),
]
