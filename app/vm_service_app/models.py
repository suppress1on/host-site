from django.db import models
from django.conf import settings

class VmInstance(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('provisioning', 'В процессе подготовки'),
        ('active', 'Активна'),
        ('error', 'Ошибка'),
        ('deleted', 'Удалена'),
    ]

    OS_CHOICES = [
        ('ubuntu', 'Ubuntu Server'),
        ('centos', 'CentOS Stream'),
        ('debian', 'Debian'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vm_instances')
    name = models.CharField(max_length=255, unique=True)
    ram_gb = models.IntegerField()
    vcpu = models.IntegerField()
    disk_gb = models.IntegerField(default=50) # Добавлено
    os_type = models.CharField(max_length=50, choices=OS_CHOICES, default='ubuntu') # Добавлено
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cost_per_month = models.DecimalField(max_digits=8, decimal_places=2)

    ansible_stdout = models.TextField(blank=True, null=True)
    ansible_stderr = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (User: {self.user.username}, Status: {self.get_status_display()})"

    class Meta:
        verbose_name = "Виртуальная машина"
        verbose_name_plural = "Виртуальные машины"
