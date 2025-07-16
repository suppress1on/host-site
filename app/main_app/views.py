# host-site/app/main_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required # Убедитесь, что этот импорт есть
from vm_service_app.models import VmInstance
from storage_app.models import DiskSpaceInstance # <--- ДОБАВЛЕНО: Импортируем модель DiskSpaceInstance

@login_required
def dashboard_view(request):
    # Получаем все ВМ, принадлежащие текущему пользователю, исключая удаленные
    user_vms = VmInstance.objects.filter(user=request.user).exclude(status='deleted').order_by('-created_at')

    # <--- ДОБАВЛЕНО: Получаем все экземпляры дискового пространства, принадлежащие текущему пользователю
    user_disk_spaces = DiskSpaceInstance.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'user_vms': user_vms,
        'disk_spaces': user_disk_spaces, # <--- ДОБАВЛЕНО: Передаем список экземпляров дискового пространства
    }
    return render(request, 'main_app/dashboard.html', context)

# Добавьте другие view-функции main_app, если они есть (например, index_view, landing_page_view)
# Если у вас есть index_view, который перенаправляет на dashboard_view, убедитесь, что он выглядит так:
def index_view(request):
    if request.user.is_authenticated:
        return redirect('main_app:home') # 'home' - это URL для dashboard_view
    else:
        return render(request, 'main_app/landing_page.html')
