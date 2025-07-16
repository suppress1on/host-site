from django.urls import path
from . import views

app_name = 'vm_service_app'

urlpatterns = [
    path('provisioning/', views.vm_provisioning_form_view, name='vm_provisioning_form'),
    path('provision/', views.provision_vm_action, name='provision_vm_action'),
    path('<int:vm_id>/console/', views.vm_console_view, name='vm_console'),
    path('<int:vm_id>/delete/', views.delete_vm_action, name='delete_vm_action'),
]