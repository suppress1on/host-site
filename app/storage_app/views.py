# host-site/app/storage_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .forms import RequestDiskSpaceForm
from .models import DiskSpaceInstance
from django.conf import settings
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

# --- Вспомогательная функция для инициализации клиента MinIO ---
def get_minio_client():
    return boto3.client(
        's3',
        endpoint_url=f"http{'s' if settings.MINIO_SECURE else ''}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False # Для самоподписанных сертификатов или HTTP. В продакшене лучше True.
    )

# --- Форма заказа дискового пространства ---
@login_required
def request_disk_space_view(request):
    if request.method == 'POST':
        form = RequestDiskSpaceForm(request.POST)
        if form.is_valid():
            disk_space_instance = form.save(commit=False)
            disk_space_instance.user = request.user
            disk_space_instance.status = 'pending' # Статус "в ожидании"
            
            try:
                disk_space_instance.save()
                messages.info(request, f'Запрос на {disk_space_instance.allocated_gb} ГБ дискового пространства "{disk_space_instance.name}" принят.')
                
                # Попытка создать бакет MinIO сразу после сохранения
                minio_client = get_minio_client()
                bucket_name = disk_space_instance.minio_bucket_name
                
                try:
                    minio_client.create_bucket(Bucket=bucket_name)
                    disk_space_instance.status = 'active'
                    disk_space_instance.save()
                    messages.success(request, f'Дисковое пространство "{disk_space_instance.name}" успешно активировано.')
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code")
                    if error_code == 'BucketAlreadyOwnedByYou':
                        disk_space_instance.status = 'active'
                        disk_space_instance.save()
                        messages.info(request, f'Бакет для "{disk_space_instance.name}" уже существует и активирован.')
                    else:
                        logger.error(f"Ошибка MinIO при создании бакета для {disk_space_instance.name}: {e}")
                        disk_space_instance.status = 'error'
                        disk_space_instance.save()
                        messages.error(request, f'Ошибка при активации дискового пространства "{disk_space_instance.name}": {e}')
                
                return redirect('main_app:home')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении запроса или создании бакета: {e}')
                logger.error(f"Ошибка при обработке запроса дискового пространства: {e}")
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = RequestDiskSpaceForm()
    
    return render(request, 'storage_app/request_disk_space.html', {'form': form})

# --- Страница файловой системы для конкретного дискового пространства ---
@login_required
def file_system_view(request, uuid_str):
    disk_space_instance = get_object_or_404(DiskSpaceInstance, uuid=uuid_str, user=request.user)
    
    if disk_space_instance.status != 'active':
        messages.warning(request, f'Дисковое пространство "{disk_space_instance.name}" неактивно. Доступ ограничен.')
        return redirect('main_app:home')

    files = []
    try:
        minio_client = get_minio_client()
        bucket_name = disk_space_instance.minio_bucket_name
        
        # Получаем список объектов в бакете
        response = minio_client.list_objects_v2(Bucket=bucket_name)
        
        for obj in response.get('Contents', []):
            files.append({
                'name': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified']
            })
    except ClientError as e:
        logger.error(f"Ошибка MinIO при получении списка файлов для {disk_space_instance.name}: {e}")
        messages.error(request, f'Ошибка при загрузке файлов: {e}')
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении списка файлов: {e}")
        messages.error(request, f'Произошла ошибка при загрузке файлов.')

    context = {
        'disk_space_instance': disk_space_instance,
        'files': files,
        'current_path': '/',
    }
    return render(request, 'storage_app/file_system.html', context)

# --- API для загрузки файлов (POST) ---
@login_required
@require_POST
def upload_file_api(request, uuid_str):
    disk_space_instance = get_object_or_404(DiskSpaceInstance, uuid=uuid_str, user=request.user)

    if disk_space_instance.status != 'active':
        return JsonResponse({'status': 'error', 'message': 'Дисковое пространство неактивно.'}, status=400)

    if 'file' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'Файл не предоставлен.'}, status=400)

    uploaded_file = request.FILES['file']
    file_name = uploaded_file.name
    
    if (disk_space_instance.used_bytes + uploaded_file.size) > (disk_space_instance.allocated_gb * (1024**3)):
        return JsonResponse({'status': 'error', 'message': 'Превышена квота дискового пространства.'}, status=400)

    try:
        minio_client = get_minio_client()
        bucket_name = disk_space_instance.minio_bucket_name
        
        minio_client.upload_fileobj(
            uploaded_file,
            bucket_name,
            file_name,
            ExtraArgs={'ContentType': uploaded_file.content_type}
        )
        
        disk_space_instance.used_bytes += uploaded_file.size
        disk_space_instance.save()

        messages.success(request, f'Файл "{file_name}" успешно загружен.')
        return JsonResponse({'status': 'success', 'message': 'Файл успешно загружен.'})

    except ClientError as e:
        logger.error(f"Ошибка MinIO при загрузке файла {file_name} для {disk_space_instance.name}: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ошибка загрузки файла: {e}'}, status=500)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке файла {file_name}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Произошла ошибка при загрузке файла.'}, status=500)

# --- API для скачивания файлов (GET) ---
@login_required
def download_file_api(request, uuid_str, file_name):
    disk_space_instance = get_object_or_404(DiskSpaceInstance, uuid=uuid_str, user=request.user)

    if disk_space_instance.status != 'active':
        messages.error(request, 'Дисковое пространство неактивно.')
        return redirect('storage_app:file_system', uuid_str=uuid_str)

    try:
        minio_client = get_minio_client()
        bucket_name = disk_space_instance.minio_bucket_name
        
        response = minio_client.get_object(Bucket=bucket_name, Key=file_name)
        
        from django.http import StreamingHttpResponse
        import mimetypes
        
        content_type, encoding = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        response_data = StreamingHttpResponse(response.iter_chunks(), content_type=content_type)
        response_data['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response_data['Content-Length'] = response['ContentLength']
        
        return response_data

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'NoSuchKey':
            messages.error(request, f'Файл "{file_name}" не найден.')
            return redirect('storage_app:file_system', uuid_str=uuid_str)
        else:
            logger.error(f"Ошибка MinIO при скачивании файла {file_name} для {disk_space_instance.name}: {e}")
            messages.error(request, f'Ошибка скачивания файла: {e}')
            return redirect('storage_app:file_system', uuid_str=uuid_str)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при скачивании файла {file_name}: {e}")
        messages.error(request, f'Произошла ошибка при скачивании файла.')
        return redirect('storage_app:file_system', uuid_str=uuid_str)

# --- API для удаления файлов (POST) ---
@login_required
@require_POST
def delete_file_api(request, uuid_str):
    disk_space_instance = get_object_or_404(DiskSpaceInstance, uuid=uuid_str, user=request.user)

    if disk_space_instance.status != 'active':
        return JsonResponse({'status': 'error', 'message': 'Дисковое пространство неактивно.'}, status=400)

    file_name = request.POST.get('file_name')
    if not file_name:
        return JsonResponse({'status': 'error', 'message': 'Имя файла не предоставлено.'}, status=400)

    try:
        minio_client = get_minio_client()
        bucket_name = disk_space_instance.minio_bucket_name
        
        try:
            obj_info = minio_client.head_object(Bucket=bucket_name, Key=file_name)
            file_size = obj_info['ContentLength']
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == 'NotFound':
                return JsonResponse({'status': 'error', 'message': f'Файл "{file_name}" не найден.'}, status=404)
            else:
                raise

        minio_client.delete_object(Bucket=bucket_name, Key=file_name)
        
        disk_space_instance.used_bytes -= file_size
        if disk_space_instance.used_bytes < 0:
            disk_space_instance.used_bytes = 0
        disk_space_instance.save()

        messages.success(request, f'Файл "{file_name}" успешно удален.')
        return JsonResponse({'status': 'success', 'message': 'Файл успешно удален.'})

    except ClientError as e:
        logger.error(f"Ошибка MinIO при удалении файла {file_name} для {disk_space_instance.name}: {e}")
        return JsonResponse({'status': 'error', 'message': f'Ошибка удаления файла: {e}'}, status=500)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при удалении файла {file_name}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Произошла ошибка при удалении файла.'}, status=500)

# --- Функция для удаления дискового пространства ---
@login_required
@require_POST
def delete_disk_space_action(request, uuid_str):
    disk_space_instance = get_object_or_404(DiskSpaceInstance, uuid=uuid_str, user=request.user)
    
    try:
        minio_client = get_minio_client()
        bucket_name = disk_space_instance.minio_bucket_name
        
        # Сначала удаляем все объекты в бакете
        objects_to_delete = minio_client.list_objects_v2(Bucket=bucket_name).get('Contents', [])
        if objects_to_delete:
            delete_keys = [{'Key': obj['Key']} for obj in objects_to_delete]
            # MinIO API требует BatchDelete для удаления более 1000 объектов,
            # но для демонстрации этого достаточно.
            minio_client.delete_objects(Bucket=bucket_name, Delete={'Objects': delete_keys})
        
        # Затем удаляем сам бакет
        minio_client.delete_bucket(Bucket=bucket_name)
        
        # И только после этого удаляем запись из БД
        disk_space_instance.delete()
        messages.success(request, f'Дисковое пространство "{disk_space_instance.name}" успешно удалено.')
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'NoSuchBucket':
            # Если бакет уже не существует, просто удаляем запись из БД
            disk_space_instance.delete()
            messages.info(request, f'Бакет для "{disk_space_instance.name}" не найден, запись удалена из БД.')
        else:
            logger.error(f"Ошибка MinIO при удалении дискового пространства {disk_space_instance.name}: {e}")
            messages.error(request, f'Ошибка при удалении дискового пространства "{disk_space_instance.name}": {e}')
            disk_space_instance.status = 'deletion_error' # <--- ИЗМЕНЕНО
            disk_space_instance.save()
    except Exception as e:
        logger.error(f"Неожиданная ошибка при удалении дискового пространства {disk_space_instance.name}: {e}")
        messages.error(request, f'Произошла ошибка при удалении дискового пространства "{disk_space_instance.name}".')
        disk_space_instance.status = 'deletion_error' # <--- ИЗМЕНЕНО
        disk_space_instance.save()
        
    return redirect('main_app:home')