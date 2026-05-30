"""
Commande Django : python manage.py runassistant
Lance l'assistant vocal ET le serveur web dans le même processus.
"""
import threading
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Lance l'assistant vocal Aria avec le serveur web"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("""
╔══════════════════════════════════════════╗
║      Assistant Vocal Aria — Démarrage    ║
║   Dashboard → http://localhost:8000      ║
╚══════════════════════════════════════════╝
        """))

        # Démarre l'assistant dans un thread séparé
        from core.assistant import get_assistant
        from api.consumers import broadcast_to_websocket

        assistant = get_assistant()
        assistant.set_ws_broadcast(broadcast_to_websocket)

        assistant_thread = threading.Thread(
            target=assistant.start,
            daemon=True,
            name="AssistantThread"
        )
        assistant_thread.start()
        self.stdout.write(self.style.SUCCESS("✓ Assistant vocal démarré"))

        # Lance le serveur ASGI Daphne (WebSocket + HTTP)
        self.stdout.write(self.style.SUCCESS("✓ Serveur web démarré sur http://localhost:8000\n"))

        from daphne.cli import CommandLineInterface
        cli = CommandLineInterface()
        cli.run(["config.asgi:application", "-b", "0.0.0.0", "-p", "8000"])
