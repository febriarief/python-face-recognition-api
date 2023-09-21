from django.db import models

class liveness_logs(models.Model):
    filename = models.CharField(max_length=500)
    score = models.FloatField()
    result = models.BooleanField()
    message = models.TextField(blank=True, null=True)
    exec_time = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

class compare_logs(models.Model):
    filename_1 = models.CharField(max_length=500)
    filename_2 = models.CharField(max_length=500)
    face_distance = models.FloatField()
    tolerance = models.FloatField()
    result = models.BooleanField()
    message = models.TextField(blank=True, null=True)
    exec_time = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
