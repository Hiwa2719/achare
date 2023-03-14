import random

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BlockedIPNumber, SMSTicket, FailedTries
from .serializers import SMSTicketSerializer, UserSerializer
from .utils import ip_extractor

User = get_user_model()


def is_blocked(request, number):
    ip = ip_extractor(request)
    queryset = BlockedIPNumber.objects.filter(Q(ip=ip) | Q(number=number))
    if queryset:
        return queryset.first().is_blocked()


class BlockHandlerMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            self.number = request.POST.get('number')
            if self.number:
                if is_blocked(request, self.number):
                    return JsonResponse({'message': _('We are sorry you have been blocked for an hour.')},
                                        status=status.HTTP_403_FORBIDDEN)
            else:
                return JsonResponse({'message': _('phone number is required')}, status=status.HTTP_400_BAD_REQUEST)
        return super().dispatch(request, *args, **kwargs)


class CheckNumberView(BlockHandlerMixin, APIView):
    def post(self, request, *args, **kwargs):
        if User.objects.filter(number=self.number).exists():
            return Response({'message': _('already exists')})

        code = self.generate_code()
        data = {'code': code, 'number': self.number}
        serializer = SMSTicketSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.send_sms(self.number, code)
        serializer.save()
        return Response({'message': _('you should receive an sms in a moment')})

    def generate_code(self):
        code = random.randint(100000, 999999)
        if SMSTicket.objects.filter(number=self.number, code=code).exists():
            return self.generate_code()
        return code

    def send_sms(self, number, code):
        """this method handles sending sms and connecting to sms module"""
        # todo
        print('sending SMS')
        print(f'Code is: {code}')


class CodeVerificationView(BlockHandlerMixin, APIView):
    def post(self, request, *args, **kwargs):
        code = request.data.get('code')

        sms_objs = SMSTicket.objects.filter(number=self.number, code=code)
        if sms_objs.exists():
            if sms_objs.latest('created').is_valid():
                return Response({'message': _('correct code')})
            sms_objs.delete()
            return self.expired_code()

        FailedTries.objects.create(ip=ip_extractor(self.request), number=self.number, type='sms')
        return Response({'message': _('provided code is wrong please try again.')},
                        status=status.HTTP_406_NOT_ACCEPTABLE)

    def expired_code(self):
        return Response({'message': _('provided code is not valid anymore. please request new one')},
                        status=status.HTTP_406_NOT_ACCEPTABLE)


class SignupView(CodeVerificationView):
    def post(self, request, *args, **kwargs):
        code = request.data.get('code')

        sms_objs = SMSTicket.objects.filter(number=self.number, code=code)
        valid_code = sms_objs.first().is_valid() if sms_objs.exists() else False
        if not valid_code:
            return self.expired_code()

        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            sms_objs.delete()
            return self.is_valid(serializer)
        return Response({'message': serializer.errors}, status=status.HTTP_406_NOT_ACCEPTABLE)

    def is_valid(self, serializer):
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response({'token': token.key})


class LoginView(BlockHandlerMixin, APIView):
    def post(self, request, *args, **kwargs):
        password = request.data.get('password')

        user = authenticate(request, username=self.number, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})

        FailedTries.objects.create(ip=ip_extractor(request), number=self.number, type='login')
        return Response({'message': _('provided credentials are wrong please try again.')},
                        status=status.HTTP_406_NOT_ACCEPTABLE)
