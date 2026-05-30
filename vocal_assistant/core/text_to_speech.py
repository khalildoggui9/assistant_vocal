"""
Module Text-to-Speech pyttsx3 — Fix audio device Windows.
Lance un subprocess à chaque fois pour éviter les problèmes
de changement de périphérique audio sous Windows.
"""
import sys
import logging
import subprocess
import queue
import threading
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class TextToSpeechEngine:

    SYSTEM_PHRASES = {
        "ready":          "Bonjour ! Je suis {name}, votre assistant. Comment puis-je vous aider ?",
        "listening":      "Je vous écoute.",
        "not_understood": "Désolé, je n'ai pas compris.",
        "error":          "Une erreur s'est produite.",
        "goodbye":        "Au revoir !",
    }

    def __init__(self):
        self.assistant_name = settings.ASSISTANT_NAME
        self.rate    = settings.TTS_RATE
        self.volume  = settings.TTS_VOLUME
        self._voice  = self._find_french_voice()
        self._queue  = queue.Queue()
        self._running = True
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()
        logger.info(f"TTS prêt — voix: {self._voice or 'défaut'}")

    def _find_french_voice(self) -> Optional[str]:
        """Trouve la voix française disponible."""
        try:
            import pyttsx3
            e = pyttsx3.init()
            voices = e.getProperty("voices")
            e.stop()
            for v in voices:
                if any(k in (v.id + v.name).lower()
                       for k in ["fr", "french", "hortense", "julie"]):
                    return v.id
        except Exception:
            pass
        return None

    def _speak_subprocess(self, text: str):
        """
        Parle dans un sous-processus séparé.
        Chaque appel crée un nouveau moteur pyttsx3 frais
        → fonctionne même si le périphérique audio a changé.
        """
        voice_line = f"e.setProperty('voice',{repr(self._voice)});" if self._voice else ""

        # Script Python passé en ligne de commande
        script = (
            "import pyttsx3;"
            "e=pyttsx3.init();"
            f"e.setProperty('rate',{self.rate});"
            f"e.setProperty('volume',{self.volume});"
            f"{voice_line}"
            f"e.say({repr(text)});"
            "e.runAndWait()"
        )

        flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags = subprocess.CREATE_NO_WINDOW

        try:
            subprocess.run(
                [sys.executable, "-c", script],
                timeout=30,
                creationflags=flags,
                # Pas de capture — laisse le son passer au device par défaut
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            logger.warning("TTS timeout")
        except Exception as e:
            logger.error(f"Erreur TTS subprocess: {e}")

    def _loop(self):
        """Worker — traite les messages un par un."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text:
                    self._speak_subprocess(text)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erreur worker TTS: {e}")

    def speak(self, text: str, priority: bool = False):
        if not text:
            return
        if priority:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
        self._queue.put(text)
        logger.info(f"TTS → '{text[:60]}'")

    def speak_system(self, key: str, **kwargs):
        t = self.SYSTEM_PHRASES.get(key, "")
        if t:
            self.speak(t.format(name=self.assistant_name),
                      priority=(key in ("ready", "error")))

    def speak_now(self, text: str):
        """Bloquant — attend la fin avant de continuer."""
        self._speak_subprocess(text)

    def stop(self):
        self._running = False
        logger.info("TTS arrêté.")

    @property
    def is_speaking(self):
        return not self._queue.empty()