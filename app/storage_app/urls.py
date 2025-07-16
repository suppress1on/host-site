from django.urls import path
from . import views

app_name = 'storage_app'

urlpatterns = [
    path('request/', views.request_disk_space_view, name='request_disk_space'),
    path('<uuid:uuid_str>/', views.file_system_view, name='file_system'),
    path('<uuid:uuid_str>/upload/', views.upload_file_api, name='upload_file_api'),
    path('<uuid:uuid_str>/download/<path:file_name>/', views.download_file_api, name='download_file_api'),
    path('<uuid:uuid_str>/delete/', views.delete_file_api, name='delete_file_api'),
    path('<uuid:uuid_str>/delete_instance/', views.delete_disk_space_action, name='delete_disk_space_action'),
]