from django.urls import path
from . import face_recognition

urlpatterns = [
    path('', face_recognition.checkLiveness),
]
