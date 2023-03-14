from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import SMSTicket, User


class SMSTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSTicket
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = 'first_name', 'last_name', 'email', 'number', 'password'

    def validate_password(self, password):
        validate_password(password)
        return password

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
