"""
Module Speech-to-Text avec VOSK — Stereo to Mono (Windows fix)
"""
import json
import queue
import struct
import logging
import threading
from typing import Callable, Optional
from datetime import datetime
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class SpeechToTextEngine:

    def __init__(self):
        self.model_path  = settings.VOSK_MODEL_PATH
        self.sample_rate = settings.AUDIO_SAMPLE_RATE
        self.chunk_size  = settings.AUDIO_CHUNK_SIZE
        self.mic_index   = getattr(settings, 'MIC_DEVICE_INDEX', 1)
        self.channels    = getattr(settings, 'MIC_CHANNELS', 2)
        self.wake_word   = settings.ASSISTANT_WAKE_WORD.lower()

        self._model        = None
        self._recognizer   = None
        self._is_listening = False
        self._result_queue = queue.Queue()
        self._callbacks    = []
        self._stop_event   = threading.Event()
        self._listen_thread = None

        self._load_model()

    def _load_model(self):
        path = Path(self.model_path)
        if not path.exists() or not any(path.iterdir()):
            logger.warning("Modèle Vosk introuvable. Mode simulation STT.")
            return
        try:
            from vosk import Model, KaldiRecognizer
            self._model      = Model(str(path))
            self._recognizer = KaldiRecognizer(self._model, self.sample_rate)
            self._recognizer.SetWords(True)
            logger.info(f"Vosk chargé — micro index: {self.mic_index}, channels: {self.channels}")
        except Exception as e:
            logger.error(f"Erreur chargement Vosk: {e}")

    def _stereo_to_mono(self, raw: bytes) -> bytes:
        """Convertit audio stéréo en mono (prend channel gauche)."""
        if self.channels == 1:
            return raw
        count   = len(raw) // 2  # nombre de samples int16
        samples = struct.unpack(f"<{count}h", raw)
        mono    = samples[::2]   # 1 sample sur 2
        return struct.pack(f"<{len(mono)}h", *mono)

    def _listen_loop(self):
        try:
            import pyaudio
        except ImportError:
            logger.error("pyaudio non installé")
            return

        pa     = pyaudio.PyAudio()
        stream = None

        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.mic_index,
                frames_per_buffer=self.chunk_size
            )
            stream.start_stream()
            logger.info(f"🎤 Écoute démarrée (index:{self.mic_index}, ch:{self.channels})")

            while not self._stop_event.is_set():
                raw  = stream.read(self.chunk_size, exception_on_overflow=False)
                mono = self._stereo_to_mono(raw)

                if self._recognizer.AcceptWaveform(mono):
                    result = json.loads(self._recognizer.Result())
                    text   = result.get("text", "").strip()
                    if text:
                        event = {
                            "type": "final",
                            "text": text,
                            "timestamp": datetime.now().isoformat(),
                            "contains_wake_word": self.wake_word in text.lower()
                        }
                        self._result_queue.put(event)
                        self._notify_callbacks(event)
                        logger.info(f"STT Final: '{text}'")
                else:
                    partial = json.loads(self._recognizer.PartialResult())
                    text    = partial.get("partial", "").strip()
                    if text:
                        self._notify_callbacks({
                            "type": "partial",
                            "text": text,
                            "timestamp": datetime.now().isoformat()
                        })

        except Exception as e:
            logger.error(f"Erreur micro: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()
            logger.info("🔇 Écoute arrêtée")

    def _notify_callbacks(self, data):
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Erreur callback: {e}")

    def register_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def start_continuous_recognition(self):
        if self._is_listening:
            return
        if not self._model:
            logger.warning("Vosk non disponible — mode simulation.")
            self._is_listening = True
            return
        self._stop_event.clear()
        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="Vosk-STT"
        )
        self._listen_thread.start()
        self._is_listening = True

    def stop_continuous_recognition(self):
        self._stop_event.set()
        self._is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2)

    def get_result(self, timeout=5.0):
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_listening(self):
        return self._is_listening