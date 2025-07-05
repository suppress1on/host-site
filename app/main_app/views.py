# host-site/app/main_app/views.py
from django.shortcuts import render
from vm_service_app.models import VmInstance 

def index_view(request):
    if request.user.is_authenticated:
        user_vms = VmInstance.objects.filter(user=request.user).exclude(status='deleted').order_by('-created_at')
        return render(request, 'main_app/dashboard.html', {'user_vms': user_vms})
    else:
        return render(request, 'main_app/landing_page.html')