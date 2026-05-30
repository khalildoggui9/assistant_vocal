"""
API REST Django — Endpoints de contrôle de l'assistant vocal
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class AssistantStatusView(APIView):
    """GET /api/status/ — Statut complet de l'assistant."""

    def get(self, request):
        try:
            from core.assistant import get_assistant
            assistant = get_assistant()
            return Response(assistant.get_status())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommandView(APIView):
    """POST /api/command/ — Envoie une commande textuelle à l'assistant."""

    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response(
                {"error": "Champ 'text' requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            from core.assistant import get_assistant
            assistant = get_assistant()
            command = assistant.command_engine.process(text)
            if command:
                assistant.handlers.dispatch(command)
                return Response({
                    "success": True,
                    "command": command.to_dict()
                })
            return Response({
                "success": False,
                "message": "Commande non reconnue."
            })
        except Exception as e:
            logger.error(f"Erreur API command: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpeakView(APIView):
    """POST /api/speak/ — Synthétise un texte via TTS."""

    def post(self, request):
        text = request.data.get("text", "").strip()
        priority = request.data.get("priority", False)
        if not text:
            return Response(
                {"error": "Champ 'text' requis."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            from core.assistant import get_assistant
            assistant = get_assistant()
            assistant.tts.speak(text, priority=priority)
            return Response({"success": True, "text": text})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IntentsView(APIView):
    """GET /api/intents/ — Liste tous les intents supportés."""

    def get(self, request):
        try:
            from core.assistant import get_assistant
            assistant = get_assistant()
            intents = assistant.command_engine.get_all_intents()
            return Response({"intents": intents, "count": len(intents)})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TranscribeView(APIView):
    """POST /api/transcribe/ — Reconnaissance vocale ponctuelle."""

    def post(self, request):
        try:
            from core.assistant import get_assistant
            assistant = get_assistant()
            result = assistant.stt.recognize_once()
            if result:
                return Response({"success": True, "result": result})
            return Response({"success": False, "message": "Aucune parole détectée."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
