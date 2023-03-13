from rest_framework import serializers

from .models import SMSTicket


class SMSTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSTicket
        fields = '__all__'
