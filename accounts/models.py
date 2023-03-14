from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import number_validator


class User(AbstractUser):
    number = models.CharField(_('phone number'), max_length=11, unique=True, validators=[number_validator])
    USERNAME_FIELD = 'number'


class SMSTicket(models.Model):
    number = models.CharField(max_length=11, validators=[number_validator])
    code = models.CharField(max_length=6)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [UniqueConstraint(fields=['number', 'code'], name='number_code_uniqueness')]

    def __str__(self):
        return self.number

    def is_valid(self, hours=1):
        return self.created + timedelta(hours=hours) > timezone.now()


class BaseAbstractModel(models.Model):
    """this model is used as an abstract model for BlockedIPNumber, FailedTries models"""
    ip = models.GenericIPAddressField(blank=True, null=True)
    number = models.CharField(max_length=11, blank=True, validators=[number_validator])
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.ip or self.number


class BlockedIPNumber(BaseAbstractModel):
    """this model represents ips or number which have been blocked because of too many tries"""

    def __str__(self):
        return self.ip or self.number

    def is_blocked(self, hours=1):
        """if current time is less than created time plus hours returns True otherwise it deletes object
        and returns False"""
        result = self.created + timedelta(hours=hours) > timezone.now()
        if not result:
            self.delete()
        return result


class FailedTries(BaseAbstractModel):
    """this model saves failed tries either login or sms verification"""
    TYPE_CHOICES = (
        ('login', 'login'),
        ('sms', 'sms verification')
    )
    type = models.CharField(default='login', choices=TYPE_CHOICES, max_length=5)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        queryset = self.__class__.objects.filter(Q(ip=self.ip) | Q(number=self.number)).order_by('-created')
        try:
            third = list(queryset)[2]
            if third.created + timedelta(minutes=5) > self.created:
                BlockedIPNumber.objects.create(ip=self.ip, number=self.number)
        except IndexError:
            pass
