import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)
ASSISTANT_GROUP = "assistant_broadcast"


class AssistantConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add(ASSISTANT_GROUP, self.channel_name)
        await self.accept()
        await self._send_status()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ASSISTANT_GROUP, self.channel_name)

    async def receive(self, text_data):
        try:
            data   = json.loads(text_data)
            action = data.get("action")

            if action == "get_status":
                await self._send_status()

            elif action == "manual_command":
                text = data.get("text", "").strip()
                if text:
                    await database_sync_to_async(self._run_command)(text)
        except Exception as e:
            logger.error(f"Erreur receive: {e}")

    async def _send_status(self):
        try:
            s = await database_sync_to_async(self._get_status)()
            await self.send(text_data=json.dumps({"type": "status", "data": s}))
        except Exception as e:
            logger.error(f"Erreur status: {e}")

    def _get_status(self):
        from core.assistant import get_assistant
        return get_assistant().get_status()

    def _run_command(self, text):
        import threading
        from core.assistant import get_assistant
        threading.Thread(
            target=get_assistant()._process_command,
            args=(text, "keyboard"), daemon=True
        ).start()

    # ── Reçoit les broadcasts et les envoie au client ──────────────────
    async def assistant_event(self, event):
        """
        event contient :
          - type        = "assistant_event"  (pour channels)
          - event_type  = le vrai type (state_change, ai_response, ...)
          - data        = le contenu
        """
        await self.send(text_data=json.dumps({
            "type": event.get("event_type"),
            "data": event.get("data", {})
        }))


def broadcast_to_websocket(msg: dict):
    """
    Appelé depuis l'assistant pour diffuser un événement.
    msg = {"type": "ai_response", "data": {...}, "timestamp": ...}
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(ASSISTANT_GROUP, {
            "type":       "assistant_event",   # handler dans le consumer
            "event_type": msg.get("type"),     # vrai type conservé
            "data":       msg.get("data", {}), # contenu
        })
    except Exception as e:
        logger.error(f"Erreur broadcast: {e}")