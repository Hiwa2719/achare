from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('check-number/', views.CheckNumberView.as_view(), name='check-number'),
    path('code-verification/', views.CodeVerificationView.as_view(), name='code-verification')
]
