from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string
from django.utils import timezone

class CustomUser(AbstractUser):
    country = models.CharField(max_length=100, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    two_fa_code = models.CharField(max_length=6, blank=True, null=True)
    two_fa_code_expires = models.DateTimeField(blank=True, null=True)

    def generate_two_fa_code(self):
        code = ''.join(random.choices(string.digits, k=6))
        self.two_fa_code = code
        self.two_fa_code_expires = timezone.now() + timezone.timedelta(minutes=5)
        self.save()
        return code

    def __str__(self):
        return self.username or self.email