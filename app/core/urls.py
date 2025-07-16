from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')), # Главная страница проекта
    path('auth/', include('auth_app.urls', namespace='auth')),
    path('vm/', include('vm_service_app.urls', namespace='vm_service_app')),
    path('storage/', include('storage_app.urls')),
    path('', include('main_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

