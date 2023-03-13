import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def number_validator(number):
    if not re.match(r'^09\d{9}$', number):
        raise ValidationError(
            _('%(number)s is not a valid phone number. correct phone number is like: 09904856953'),
            params={'number': number},
        )


def ip_extractor(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
