"""
Orchestrateur Principal — Assistant Vocal IA (Groq + Vosk + pyttsx3)
Pipeline : Vosk STT → Groq Llama 3 → pyttsx3 TTS
"""
import os
import sys
import logging
import threading
import time
from enum import Enum, auto
from typing import Optional
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from core.speech_to_text import SpeechToTextEngine
from core.text_to_speech import TextToSpeechEngine
from core.gpio_controller import GPIOController
from core.ai_engine import AIEngine

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    IDLE       = auto()
    LISTENING  = auto()
    PROCESSING = auto()
    SPEAKING   = auto()
    ERROR      = auto()
    SHUTDOWN   = auto()


class VocalAssistant:

    def __init__(self):
        self.name      = settings.ASSISTANT_NAME
        self.wake_word = settings.ASSISTANT_WAKE_WORD
        self._state    = AssistantState.IDLE
        self._running  = False
        self._lock     = threading.Lock()
        self._ws_broadcast: Optional[callable] = None

        logger.info(f"Initialisation de {self.name}...")
        self._init_components()

    def _init_components(self):
        self.tts = TextToSpeechEngine()
        self.ai  = AIEngine()
        self.stt = SpeechToTextEngine()
        self.stt.register_callback(self._on_speech_result)

        self.gpio = GPIOController(
            status_pin=settings.LED_STATUS_PIN,
            listen_pin=settings.LED_LISTEN_PIN,
            button_pin=settings.BUTTON_PIN,
        )
        self.gpio.set_button_callback(self._on_button_press)
        logger.info(f"Composants prêts — IA disponible: {self.ai.is_available}")

    # ── State ──────────────────────────────────────────────────────────

    def _set_state(self, new_state: AssistantState):
        with self._lock:
            old = self._state
            self._state = new_state
        self._broadcast_event("state_change", {
            "previous": old.name, "current": new_state.name,
            "timestamp": datetime.now().isoformat(),
        })
        self.gpio.set_status_led(new_state != AssistantState.SHUTDOWN)
        self.gpio.set_listen_led(new_state == AssistantState.LISTENING)

    # ── Speech callback ────────────────────────────────────────────────

    def _on_speech_result(self, result: dict):
        """Appelé par Vosk à chaque résultat STT."""
        if result["type"] == "partial":
            # Affiche les partiels seulement en mode LISTENING
            if self._state == AssistantState.LISTENING:
                self._broadcast_event("transcription_partial", result)
            return

        if result["type"] == "final":
            text = result.get("text", "").strip()
            if not text:
                return

            if self._state == AssistantState.IDLE:
                # En veille : on cherche le mot de réveil
                if self.wake_word in text.lower():
                    self._set_state(AssistantState.LISTENING)
                    self.tts.speak("Je vous écoute.")
                return

            if self._state == AssistantState.LISTENING:
                # Affiche ce que Vosk a entendu (vocal uniquement)
                self._broadcast_event("transcription_final", {
                    "text":   text,
                    "heard":  text,
                    "source": "voice",
                })
                threading.Thread(
                    target=self._process_command,
                    args=(text,), daemon=True
                ).start()

    # ── Core processing ────────────────────────────────────────────────

    def _process_command(self, text: str, source: str = "voice"):
        """Pipeline : texte → IA Groq → réponse vocale. Répond TOUJOURS."""
        self._set_state(AssistantState.PROCESSING)

        # Si commande vient du clavier → affiche dans le dashboard
        if source == "keyboard":
            self._broadcast_event("transcription_final", {
                "text":   text,
                "heard":  text,
                "source": "keyboard",
            })

        # Retire le mot de réveil si présent
        clean = text.lower().replace(self.wake_word, "").strip(" ,.")

        # Si après nettoyage il ne reste rien
        if not clean:
            self.tts.speak("Je vous écoute, posez votre question.")
            self._set_state(AssistantState.IDLE)
            return

        try:
            # Commandes système locales
            if self._handle_local_command(clean):
                return

            # Broadcast — l'IA réfléchit
            self._broadcast_event("ai_thinking", {
                "heard": text,
                "cleaned": clean,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"IA reçoit: '{clean}'")

            # Appel Groq — répond toujours
            response = self.ai.ask(clean)

            if not response:
                response = "Je n'ai pas pu formuler une réponse. Essayez de reformuler."

            self._set_state(AssistantState.SPEAKING)
            self._broadcast_event("ai_response", {
                "question": clean,
                "answer":   response,
                "timestamp": datetime.now().isoformat(),
            })

            logger.info(f"IA répond: '{response[:80]}'")
            self.tts.speak(response)

        except Exception as e:
            logger.error(f"Erreur traitement: {e}")
            self.tts.speak("Une erreur s'est produite, réessayez.")
        finally:
            if self._state != AssistantState.SHUTDOWN:
                self._set_state(AssistantState.IDLE)

    def _handle_local_command(self, text: str) -> bool:
        """Commandes traitées localement sans IA."""
        t = text.lower()
        if any(w in t for w in ["au revoir", "bonne nuit", "arrête toi", "shutdown"]):
            self.tts.speak_now("Au revoir !")
            self.stop()
            return True
        if "efface la mémoire" in t or "réinitialise" in t:
            self.ai.reset_history()
            self.tts.speak("J'ai effacé notre historique.")
            self._set_state(AssistantState.IDLE)
            return True
        return False

    # ── Button callback ────────────────────────────────────────────────

    def _on_button_press(self):
        if self._state == AssistantState.IDLE:
            self._set_state(AssistantState.LISTENING)
            self.tts.speak("Je vous écoute.")
        elif self._state == AssistantState.LISTENING:
            self._set_state(AssistantState.IDLE)

    # ── WebSocket ──────────────────────────────────────────────────────

    def _broadcast_event(self, event_type: str, data: dict):
        if self._ws_broadcast:
            try:
                self._ws_broadcast({
                    "type": event_type, "data": data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    def set_ws_broadcast(self, cb):
        self._ws_broadcast = cb

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._set_state(AssistantState.IDLE)
        self.gpio.set_status_led(True)
        self.stt.start_continuous_recognition()
        self.tts.speak(
            f"Bonjour ! Je suis {self.name}. "
            f"Dites {self.wake_word} pour m'activer."
        )
        logger.info(f"🚀 {self.name} prêt — mot de réveil: '{self.wake_word}'")
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        self._running = False
        self._set_state(AssistantState.SHUTDOWN)
        self.stt.stop_continuous_recognition()
        self.tts.stop()
        self.gpio.cleanup()
        logger.info(f"{self.name} arrêté.")

    @property
    def state(self): return self._state.name

    def get_status(self) -> dict:
        return {
            "name":         self.name,
            "state":        self.state,
            "wake_word":    self.wake_word,
            "is_listening": self._state == AssistantState.LISTENING,
            "ai_available": self.ai.is_available,
            "gpio":         self.gpio.get_state(),
            "timestamp":    datetime.now().isoformat(),
        }


# ── Singleton ──────────────────────────────────────────────────────────
_instance: Optional[VocalAssistant] = None
_lock = threading.Lock()

def get_assistant() -> VocalAssistant:
    global _instance
    with _lock:
        if _instance is None:
            _instance = VocalAssistant()
    return _instance


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    get_assistant().start()