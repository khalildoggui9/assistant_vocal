"""
Handlers des Commandes Vocales
Logique métier pour chaque intent reconnu par le moteur de commandes.
"""
import os
import math
import logging
import subprocess
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from commands.engine import VocalCommand
    from core.text_to_speech import TextToSpeechEngine

logger = logging.getLogger(__name__)

# Noms des mois en français
MOIS_FR = [
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


class CommandHandlers:
    """
    Collection de handlers pour tous les intents supportés.
    Chaque méthode handle_* correspond à un intent.
    """

    def __init__(self, tts_engine: "TextToSpeechEngine"):
        self.tts = tts_engine
        self._active_timers: dict = {}

    def dispatch(self, command: "VocalCommand") -> bool:
        """
        Dispatche une commande vers son handler.
        Retourne True si un handler a été trouvé.
        """
        intent = command.intent
        handler_map = {
            "query.time": self.handle_time,
            "query.date": self.handle_date,
            "query.weather": self.handle_weather,
            "control.light.on": self.handle_light_on,
            "control.light.off": self.handle_light_off,
            "utility.timer": self.handle_timer,
            "media.music.play": self.handle_play_music,
            "media.music.stop": self.handle_stop_music,
            "control.volume.up": self.handle_volume_up,
            "control.volume.down": self.handle_volume_down,
            "utility.calculate": self.handle_calculate,
            "system.shutdown": self.handle_shutdown,
        }

        handler = handler_map.get(intent)
        if handler:
            try:
                handler(command)
                return True
            except Exception as e:
                logger.error(f"Erreur handler {intent}: {e}")
                self.tts.speak_system("error")
                return False
        return False

    # ------------------------------------------------------------------ #
    #  Heure & Date                                                        #
    # ------------------------------------------------------------------ #

    def handle_time(self, command: "VocalCommand"):
        now = datetime.now()
        heure = now.hour
        minute = now.minute
        if minute == 0:
            msg = f"Il est {heure} heures."
        elif minute == 30:
            msg = f"Il est {heure} heures et demie."
        elif minute == 15:
            msg = f"Il est {heure} heures et quart."
        else:
            msg = f"Il est {heure} heures {minute} minutes."
        self.tts.speak(msg)

    def handle_date(self, command: "VocalCommand"):
        now = datetime.now()
        jour_semaine = JOURS_FR[now.weekday()]
        msg = f"Nous sommes le {jour_semaine} {now.day} {MOIS_FR[now.month]} {now.year}."
        self.tts.speak(msg)

    # ------------------------------------------------------------------ #
    #  Météo                                                               #
    # ------------------------------------------------------------------ #

    def handle_weather(self, command: "VocalCommand"):
        city = command.entities.get("city", "votre ville")
        # En production : appel à une API météo comme OpenWeatherMap
        self.tts.speak(
            f"Je consulte la météo pour {city}. "
            "Cette fonctionnalité nécessite une clé API météo configurée."
        )

    # ------------------------------------------------------------------ #
    #  Contrôle GPIO (Lumières)                                           #
    # ------------------------------------------------------------------ #

    def handle_light_on(self, command: "VocalCommand"):
        try:
            from core.gpio_controller import GPIOController
            GPIOController.set_light(True)
            self.tts.speak("J'allume la lumière.")
        except ImportError:
            logger.warning("GPIO non disponible (hors Raspberry Pi)")
            self.tts.speak("Simulation : lumière allumée.")

    def handle_light_off(self, command: "VocalCommand"):
        try:
            from core.gpio_controller import GPIOController
            GPIOController.set_light(False)
            self.tts.speak("J'éteins la lumière.")
        except ImportError:
            logger.warning("GPIO non disponible (hors Raspberry Pi)")
            self.tts.speak("Simulation : lumière éteinte.")

    # ------------------------------------------------------------------ #
    #  Timer                                                               #
    # ------------------------------------------------------------------ #

    def handle_timer(self, command: "VocalCommand"):
        import threading

        duration_str = command.entities.get("duration", "")
        unit = command.entities.get("unit", "minute")

        try:
            duration = int("".join(filter(str.isdigit, command.text)))
        except (ValueError, TypeError):
            duration = 5

        # Conversion en secondes
        multipliers = {
            "heure": 3600, "h": 3600,
            "minute": 60, "min": 60, "m": 60,
            "seconde": 1, "s": 1
        }
        seconds = duration * multipliers.get(unit.lower(), 60)

        timer_id = f"timer_{datetime.now().timestamp()}"

        def _timer_done():
            self.tts.speak(f"Votre minuteur de {duration} {unit}s est terminé !", priority=True)
            self._active_timers.pop(timer_id, None)

        timer = threading.Timer(seconds, _timer_done)
        timer.daemon = True
        timer.start()
        self._active_timers[timer_id] = timer

        self.tts.speak(f"Minuteur de {duration} {unit}s lancé.")

    # ------------------------------------------------------------------ #
    #  Musique & Volume                                                    #
    # ------------------------------------------------------------------ #

    def handle_play_music(self, command: "VocalCommand"):
        query = command.entities.get("query", "")
        if query:
            self.tts.speak(f"Je lance {query}.")
        else:
            self.tts.speak("Je lance la musique.")
        # En production : intégration Spotify, VLC, MPD...

    def handle_stop_music(self, command: "VocalCommand"):
        self.tts.speak("J'arrête la musique.")
        try:
            subprocess.run(["pkill", "-f", "mpg123"], check=False)
            subprocess.run(["pkill", "-f", "vlc"], check=False)
        except Exception:
            pass

    def handle_volume_up(self, command: "VocalCommand"):
        try:
            subprocess.run(["amixer", "set", "Master", "10%+"], check=False, capture_output=True)
        except Exception:
            pass
        self.tts.speak("Volume augmenté.")

    def handle_volume_down(self, command: "VocalCommand"):
        try:
            subprocess.run(["amixer", "set", "Master", "10%-"], check=False, capture_output=True)
        except Exception:
            pass
        self.tts.speak("Volume baissé.")

    # ------------------------------------------------------------------ #
    #  Calcul                                                              #
    # ------------------------------------------------------------------ #

    def handle_calculate(self, command: "VocalCommand"):
        expr_str = command.entities.get("expression", command.text)
        # Nettoyage sécurisé de l'expression
        expr_str = (expr_str
                    .replace("×", "*").replace("÷", "/")
                    .replace("plus", "+").replace("moins", "-")
                    .replace("fois", "*").replace("divisé par", "/"))

        import re
        numbers = re.findall(r"\d+\.?\d*", expr_str)
        operators = re.findall(r"[+\-*/]", expr_str)

        if len(numbers) >= 2 and operators:
            try:
                a, b = float(numbers[0]), float(numbers[1])
                op = operators[0]
                results = {"+": a + b, "-": a - b, "*": a * b}
                if op == "/" and b != 0:
                    results["/"] = a / b
                result = results.get(op)
                if result is not None:
                    result_str = str(int(result)) if result == int(result) else f"{result:.2f}"
                    self.tts.speak(f"Le résultat est {result_str}.")
                    return
            except Exception:
                pass

        self.tts.speak("Je n'ai pas pu effectuer ce calcul.")

    # ------------------------------------------------------------------ #
    #  Système                                                             #
    # ------------------------------------------------------------------ #

    def handle_shutdown(self, command: "VocalCommand"):
        self.tts.speak_now("Au revoir ! À bientôt.")
        logger.info("Commande d'arrêt reçue.")
        # Signal d'arrêt gracieux (à intercepter dans le main loop)
        raise SystemExit(0)

    def handle_unknown(self, text: str):
        """Handler pour les commandes non reconnues."""
        self.tts.speak(
            "Je n'ai pas reconnu cette commande. "
            "Pouvez-vous reformuler votre demande ?"
        )
