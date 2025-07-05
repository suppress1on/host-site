from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')), # Главная страница проекта
    path('auth/', include('auth_app.urls', namespace='auth')),
    path('vm/', include('vm_service_app.urls', namespace='vm_service_app')),
]
