from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path("vocabulary/", include("vocabulary.urls")),
    path("", include("core.urls")),
    path("workouts/", include("workouts.urls")),
    path("darts/", include("darts.urls")),
]
