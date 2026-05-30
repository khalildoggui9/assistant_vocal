from django.urls import re_path
from api.consumers import AssistantConsumer

websocket_urlpatterns = [
    re_path(r"ws/assistant/$", AssistantConsumer.as_asgi()),
]
