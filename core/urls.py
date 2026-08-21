from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),

    path(
        "service-worker.js",
        TemplateView.as_view(
            template_name="service-worker.js",
            content_type="application/javascript",
        ),
        name="service_worker",
    ),

    path(
        "login/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
