"""
Contrôleur GPIO pour Raspberry Pi 3
Gère les LEDs de statut, le bouton physique et les périphériques connectés.
"""
import logging
import threading
import platform
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Détection automatique Raspberry Pi
IS_RASPBERRY_PI = platform.machine() in ("armv7l", "aarch64")


class GPIOController:
    """
    Abstraction du contrôle GPIO du Raspberry Pi 3.
    En dehors du Raspberry Pi, toutes les opérations sont simulées.
    """

    _instance: Optional["GPIOController"] = None
    _gpio_available = False

    def __init__(self, status_pin: int = 17, listen_pin: int = 27, button_pin: int = 22):
        self.status_pin = status_pin
        self.listen_pin = listen_pin
        self.button_pin = button_pin
        self._button_callback: Optional[Callable] = None
        self._state = {"status": False, "listen": False, "light": False}

        self._setup_gpio()

    def _setup_gpio(self):
        """Initialise les GPIOs si disponibles."""
        if not IS_RASPBERRY_PI:
            logger.info("Hors Raspberry Pi — GPIO en mode simulation.")
            return

        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Configuration des broches
            GPIO.setup(self.status_pin, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.listen_pin, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Interruption sur le bouton
            GPIO.add_event_detect(
                self.button_pin,
                GPIO.FALLING,
                callback=self._on_button_press,
                bouncetime=300
            )

            self._gpio_available = True
            logger.info(
                f"GPIO initialisé — Status: {status_pin}, "
                f"Listen: {listen_pin}, Button: {button_pin}"
            )

        except (ImportError, RuntimeError) as e:
            logger.warning(f"GPIO non disponible: {e}. Mode simulation.")

    def _on_button_press(self, channel: int):
        """Callback interne pour le bouton physique."""
        logger.info(f"Bouton GPIO pressé (canal {channel})")
        if self._button_callback:
            self._button_callback()

    def set_button_callback(self, callback: Callable):
        """Enregistre le callback déclenché par le bouton physique."""
        self._button_callback = callback

    def set_status_led(self, state: bool):
        """Contrôle la LED de statut (système actif)."""
        self._state["status"] = state
        if self._gpio_available:
            self.GPIO.output(self.status_pin, self.GPIO.HIGH if state else self.GPIO.LOW)
        logger.debug(f"LED status: {'ON' if state else 'OFF'}")

    def set_listen_led(self, state: bool):
        """Contrôle la LED d'écoute (microphone actif)."""
        self._state["listen"] = state
        if self._gpio_available:
            self.GPIO.output(self.listen_pin, self.GPIO.HIGH if state else self.GPIO.LOW)
        logger.debug(f"LED écoute: {'ON' if state else 'OFF'}")

    @classmethod
    def set_light(cls, state: bool):
        """
        Contrôle la lumière externe (relay ou LED via GPIO).
        Méthode de classe pour un accès simplifié depuis les handlers.
        """
        logger.info(f"Lumière: {'ON' if state else 'OFF'}")
        # En production : piloter un relais sur une broche spécifique
        # GPIO.output(LIGHT_RELAY_PIN, GPIO.HIGH if state else GPIO.LOW)

    def blink(self, pin: str = "status", times: int = 3, interval: float = 0.3):
        """Fait clignoter une LED en arrière-plan."""
        def _blink():
            setter = self.set_status_led if pin == "status" else self.set_listen_led
            for _ in range(times):
                setter(True)
                threading.Event().wait(interval)
                setter(False)
                threading.Event().wait(interval)

        t = threading.Thread(target=_blink, daemon=True)
        t.start()

    def get_state(self) -> dict:
        """Retourne l'état courant de tous les GPIO."""
        return dict(self._state)

    def cleanup(self):
        """Libère les ressources GPIO."""
        if self._gpio_available:
            self.set_status_led(False)
            self.set_listen_led(False)
            self.GPIO.cleanup()
            logger.info("GPIO libérés.")
