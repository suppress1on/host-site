import subprocess
import os
import uuid
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import VmInstance
import json


# --- VM Provisioning Form View (Отображение формы) ---
@login_required
def vm_provisioning_form_view(request):
    default_vm_name = f'my_vm_{request.user.username}_{uuid.uuid4().hex[:8]}'
    return render(request, 'vm_service_app/vm_provisioning.html', {
        'vm_name': default_vm_name,
        'cpu_cores': 2,
        'ram_gb': 4,
        'disk_gb': 50,
        'os_type': 'ubuntu',
    })

# --- Provision VM Action (Обработка заказа и запуск Ansible) ---
@login_required
@require_POST
def provision_vm_action(request):
    user_provided_vm_name = request.POST.get('vm_name', '').strip()
    cpu_cores = int(request.POST.get('cpu_cores', '2'))
    ram_gb = int(request.POST.get('ram_gb', '4'))
    disk_gb = int(request.POST.get('disk_gb', '50'))
    os_type = request.POST.get('os_type', 'ubuntu')

    ansible_playbook_path = os.path.join(settings.BASE_DIR_PROJECT_ROOT, 'ansible', 'provision_vm.yml')
    ansible_inventory_path = os.path.join(settings.BASE_DIR_PROJECT_ROOT, 'ansible', 'inventory.ini')
    ansible_vault_password_file = os.path.expanduser('~/.ansible/vault_pass.txt')

    if user_provided_vm_name:
        vm_name = f'{user_provided_vm_name}-{uuid.uuid4().hex[:8]}'
    else:
        vm_name = f'vm-{request.user.username}-{uuid.uuid4().hex[:8]}'

    try:
        vm_instance = VmInstance.objects.create(
            user=request.user,
            name=vm_name,
            ram_gb=ram_gb,
            vcpu=cpu_cores,
            disk_gb=disk_gb,
            os_type=os_type,
            cost_per_month=0.00,
            status='pending'
        )
        messages.info(request, f'Заказ на ВМ "{vm_instance.name}" принят и находится в обработке.')
    except Exception as e:
        messages.error(request, f'Ошибка сохранения заказа ВМ: {e}')
        return redirect('main_app:home')

    extra_vars = {
        'vm_name': vm_name,
        'cpu_cores': cpu_cores,
        'ram_gb': ram_gb,
        'disk_gb': disk_gb,
        'os_type': os_type,
        'vm_db_id': vm_instance.pk,
    }
    extra_vars_json = json.dumps(extra_vars)

    try:
        command = [
            'ansible-playbook',
            '-i', ansible_inventory_path,
            ansible_playbook_path,
            '--extra-vars', extra_vars_json,
            '--vault-password-file', ansible_vault_password_file
        ]

        print(f"Executing Ansible command: {' '.join(command)}")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        # Фильтрация stderr от известных предупреждений
        cleaned_stderr = result.stderr
        if "[WARNING]: Platform linux on host localhost is using the discovered Python interpreter" in cleaned_stderr:
            cleaned_stderr = ""

        vm_instance.status = 'active'
        vm_instance.ansible_stdout = result.stdout
        vm_instance.ansible_stderr = cleaned_stderr # Сохраняем очищенный stderr
        vm_instance.save()
        messages.success(request, f'ВМ "{vm_instance.name}" успешно создана и настроена. RAM: {ram_gb}GB, CPU: {cpu_cores}.')

        return redirect('main_app:home')

    except subprocess.CalledProcessError as e:
        vm_instance.status = 'error'
        vm_instance.ansible_stdout = e.stdout
        vm_instance.ansible_stderr = e.stderr
        vm_instance.save()
        error_message = f"Ansible exited with code {e.returncode}.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        messages.error(request, f'Ошибка при выполнении Ansible Playbook для ВМ "{vm_instance.name}": {e.stderr}')
        print(f"Error during Ansible execution: {error_message}")
        return redirect('main_app:home')

    except FileNotFoundError:
        vm_instance.status = 'error'
        vm_instance.save()
        error_message = "Ошибка: Команда 'ansible-playbook' не найдена. Убедитесь, что Ansible установлен и добавлен в PATH."
        messages.error(request, error_message)
        return redirect('main_app:home')
    except Exception as e:
        vm_instance.status = 'error'
        vm_instance.save()
        error_message = f"Произошла неожиданная ошибка: {e}"
        messages.error(request, error_message)
        print(error_message)
        return redirect('main_app:home')

# --- функция для отображения консоли ВМ ---
@login_required
def vm_console_view(request, vm_id):
    vm_instance = get_object_or_404(VmInstance, pk=vm_id, user=request.user)

    if vm_instance.status != 'active':
        messages.error(request, f'Консоль ВМ "{vm_instance.name}" недоступна. Статус: {vm_instance.get_status_display()}.')
        return redirect('main_app:home')

    return render(request, 'vm_service_app/vm_console.html', {
        'vm_instance': vm_instance,
        'ansible_stdout': vm_instance.ansible_stdout,
        'ansible_stderr': vm_instance.ansible_stderr,
        'console_output': "Интерактивная консоль пока не реализована. Вы видите логи Ansible." # Более точное сообщение
    })

# --- Функция для удаления ВМ ---
@login_required
@require_POST
def delete_vm_action(request, vm_id):
    vm_instance = get_object_or_404(VmInstance, pk=vm_id, user=request.user)

    ansible_inventory_path = os.path.join(settings.BASE_DIR_PROJECT_ROOT, 'ansible', 'inventory.ini')
    ansible_vault_password_file = os.path.expanduser('~/.ansible/vault_pass.txt')
    ansible_delete_playbook_path = os.path.join(settings.BASE_DIR_PROJECT_ROOT, 'ansible', 'delete_vm.yml')

    try:
        if vm_instance.status == 'pending' or vm_instance.status == 'provisioning':
            vm_instance.delete()
            messages.success(request, f'Запись о ВМ "{vm_instance.name}" успешно удалена из базы данных.')
        else:
            command = [
                'ansible-playbook',
                '-i', ansible_inventory_path,
                ansible_delete_playbook_path,
                '--extra-vars', json.dumps({'vm_name': vm_instance.name}),
                '--vault-password-file', ansible_vault_password_file
            ]

            print(f"Executing Ansible delete command: {' '.join(command)}")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )

            vm_instance.delete()
            messages.success(request, f'Виртуальная машина "{vm_instance.name}" успешно удалена из гипервизора и базы данных.')

    except subprocess.CalledProcessError as e:
        error_message = f"Ansible exited with code {e.returncode} during deletion.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        messages.error(request, f'Ошибка при удалении ВМ "{vm_instance.name}" из гипервизора: {e.stderr}')
        print(f"Error during Ansible deletion: {error_message}")
        vm_instance.status = 'deletion_error'
        vm_instance.ansible_stdout = e.stdout
        vm_instance.ansible_stderr = e.stderr
        vm_instance.save()

    except FileNotFoundError:
        error_message = "Ошибка: Команда 'ansible-playbook' не найдена. Убедитесь, что Ansible установлен и добавлен в PATH."
        messages.error(request, error_message)
        print(error_message)
    except Exception as e:
        error_message = f"Произошла неожиданная ошибка при удалении ВМ: {e}"
        messages.error(request, error_message)
        print(error_message)
        vm_instance.status = 'deletion_error'
        vm_instance.save()

    return redirect('main_app:home')
