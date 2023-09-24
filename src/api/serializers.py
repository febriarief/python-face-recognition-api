from rest_framework import serializers
from api.models import liveness_logs, compare_logs

class LivenessLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = liveness_logs
        fields = ("filename", "score", "result", "exec_time", "message", "created_at")

class CompareLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = compare_logs
        fields = ("filename_1", "filename_2", "face_distance", "tolerance", "result", "message", "exec_time", "created_at")
