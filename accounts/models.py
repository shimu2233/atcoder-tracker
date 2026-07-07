from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    atcoder_username = models.CharField(max_length=150, null=True, blank=True)