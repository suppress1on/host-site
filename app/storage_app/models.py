# host-site/app/storage_app/models.py

from django.db import models
from django.conf import settings
import uuid

class DiskSpaceInstance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='disk_spaces')
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    name = models.CharField(max_length=255, unique=True)
    
    allocated_gb = models.IntegerField()
    
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('active', 'Активно'),
        ('deleting', 'Удаляется'),
        ('deleted', 'Удалено'),
        ('error', 'Ошибка'),
        ('deletion_error', 'Ошибка удаления'), # <--- ДОБАВЛЕНО
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    used_bytes = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = "Экземпляр дискового пространства"
        verbose_name_plural = "Экземпляры дискового пространства"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.user.username}] {self.name} ({self.allocated_gb}GB) - {self.get_status_display()}"

    @property
    def used_gb(self):
        return round(self.used_bytes / (1024**3), 2)

    @property
    def minio_bucket_name(self):
        return f"user-{self.user.id}-{self.uuid}"
