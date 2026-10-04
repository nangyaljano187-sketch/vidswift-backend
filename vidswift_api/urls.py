from django.urls import path
from .views import health, resolve_video

urlpatterns = [
    path('api/health/', health),
    path('api/resolve/', resolve_video),
]
