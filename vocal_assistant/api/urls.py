from django.urls import path
from api import views

urlpatterns = [
    path("status/", views.AssistantStatusView.as_view(), name="api_status"),
    path("command/", views.CommandView.as_view(), name="api_command"),
    path("speak/", views.SpeakView.as_view(), name="api_speak"),
    path("intents/", views.IntentsView.as_view(), name="api_intents"),
    path("transcribe/", views.TranscribeView.as_view(), name="api_transcribe"),
]
