"""
Moteur de Reconnaissance des Commandes Vocales
Analyse le texte transcrit et dispatche vers les handlers appropriés.
"""
import re
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VocalCommand:
    """Représentation d'une commande vocale reconnue."""
    name: str
    text: str
    intent: str
    entities: dict = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "text": self.text,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }


class CommandPattern:
    """Définit un pattern de commande avec regex et extracteur d'entités."""

    def __init__(self, name: str, intent: str, patterns: list[str],
                 entity_extractors: dict[str, str] = None,
                 handler: Callable = None):
        self.name = name
        self.intent = intent
        self.patterns = [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]
        self.entity_extractors = {
            k: re.compile(v, re.IGNORECASE | re.UNICODE)
            for k, v in (entity_extractors or {}).items()
        }
        self.handler = handler

    def match(self, text: str) -> Optional[dict]:
        """Tente de matcher le texte et extrait les entités."""
        for pattern in self.patterns:
            if pattern.search(text):
                entities = {}
                for entity_name, extractor in self.entity_extractors.items():
                    match = extractor.search(text)
                    if match:
                        entities[entity_name] = match.group(1) if match.lastindex else match.group(0)
                return entities
        return None


class CommandEngine:
    """
    Moteur de reconnaissance et de dispatch des commandes vocales.
    Architecture basée sur des patterns + handlers enregistrables.
    """

    def __init__(self, wake_word: str = "aria"):
        self.wake_word = wake_word.lower()
        self._patterns: list[CommandPattern] = []
        self._global_handlers: list[Callable] = []
        self._unknown_handler: Optional[Callable] = None

        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Enregistre les commandes intégrées de l'assistant."""

        # --- Heure et Date ---
        self.register(CommandPattern(
            name="get_time",
            intent="query.time",
            patterns=[
                r"quelle heure est.?il",
                r"dis.?moi l.?heure",
                r"l.?heure actuelle",
                r"what time is it"
            ]
        ))

        self.register(CommandPattern(
            name="get_date",
            intent="query.date",
            patterns=[
                r"quelle est la date",
                r"quel jour sommes.?nous",
                r"date d.?aujourd.?hui",
                r"what.?s the date"
            ]
        ))

        # --- Météo ---
        self.register(CommandPattern(
            name="get_weather",
            intent="query.weather",
            patterns=[
                r"quel temps fait.?il",
                r"météo (à|pour|de) (.+)",
                r"prévisions météo",
                r"est-ce qu.?il va pleuvoir"
            ],
            entity_extractors={
                "city": r"météo (?:à|pour|de) (.+?)(?:\s*\?)?$"
            }
        ))

        # --- Contrôle lumières (GPIO Raspberry Pi) ---
        self.register(CommandPattern(
            name="light_on",
            intent="control.light.on",
            patterns=[
                r"allume (?:la |les )?lumi[eè]res?",
                r"mets la lumière",
                r"éclaire",
                r"turn on (?:the )?lights?"
            ]
        ))

        self.register(CommandPattern(
            name="light_off",
            intent="control.light.off",
            patterns=[
                r"(?:é|e)teins? (?:la |les )?lumi[eè]res?",
                r"coupe la lumière",
                r"turn off (?:the )?lights?"
            ]
        ))

        # --- Minuteur / Timer ---
        self.register(CommandPattern(
            name="set_timer",
            intent="utility.timer",
            patterns=[
                r"minuteur (?:de |pour )?\d+",
                r"mets un timer",
                r"rappelle.?moi dans \d+",
                r"set a timer for \d+"
            ],
            entity_extractors={
                "duration": r"(\d+)\s*(minute|heure|seconde|min|h|s)",
                "unit": r"\d+\s*(minute|heure|seconde|min|h|s)"
            }
        ))

        # --- Musique ---
        self.register(CommandPattern(
            name="play_music",
            intent="media.music.play",
            patterns=[
                r"joue (?:de la |du |une )?.+",
                r"mets (?:de la |du |une )?.+musique",
                r"lance la musique",
                r"play (?:some )?music"
            ],
            entity_extractors={
                "query": r"joue (.+)|mets (.+)musique"
            }
        ))

        self.register(CommandPattern(
            name="stop_music",
            intent="media.music.stop",
            patterns=[
                r"arrête la musique",
                r"stop (?:la )?musique",
                r"coupe le son",
                r"stop music"
            ]
        ))

        # --- Volume ---
        self.register(CommandPattern(
            name="volume_up",
            intent="control.volume.up",
            patterns=[
                r"augmente (?:le )?volume",
                r"plus fort",
                r"monte le son",
                r"volume up"
            ]
        ))

        self.register(CommandPattern(
            name="volume_down",
            intent="control.volume.down",
            patterns=[
                r"baisse (?:le )?volume",
                r"moins fort",
                r"volume down"
            ]
        ))

        # --- Calcul ---
        self.register(CommandPattern(
            name="calculate",
            intent="utility.calculate",
            patterns=[
                r"calcule? \d",
                r"combien (?:font|fait) \d",
                r"(\d+)\s*[+\-×÷\*\/]\s*(\d+)",
                r"calculate \d"
            ],
            entity_extractors={
                "expression": r"(?:calcule? |combien font? )(.+)"
            }
        ))

        # --- Arrêt système ---
        self.register(CommandPattern(
            name="shutdown",
            intent="system.shutdown",
            patterns=[
                r"(?:é|e)teins?(?:-toi)?",
                r"au revoir",
                r"bonne nuit",
                r"shutdown",
                r"goodbye"
            ]
        ))

        logger.info(f"{len(self._patterns)} commandes intégrées enregistrées.")

    def register(self, pattern: CommandPattern):
        """Enregistre un nouveau pattern de commande."""
        self._patterns.append(pattern)

    def set_unknown_handler(self, handler: Callable):
        """Définit le handler pour les commandes non reconnues."""
        self._unknown_handler = handler

    def add_global_handler(self, handler: Callable):
        """Ajoute un handler appelé pour toutes les commandes reconnues."""
        self._global_handlers.append(handler)

    def _preprocess(self, text: str) -> str:
        """Nettoie et normalise le texte transcrit."""
        text = text.strip().lower()
        # Supprime le mot de réveil en début de phrase
        text = re.sub(rf"^{re.escape(self.wake_word)}[,\.\s]+", "", text)
        # Normalise les apostrophes
        text = text.replace("'", "'").replace("`", "'")
        return text

    def process(self, text: str) -> Optional[VocalCommand]:
        """
        Analyse le texte et retourne la commande reconnue ou None.
        Dispatche automatiquement vers le handler approprié.
        """
        if not text:
            return None

        processed = self._preprocess(text)
        logger.debug(f"Traitement commande: '{processed}'")

        for pattern in self._patterns:
            entities = pattern.match(processed)
            if entities is not None:
                command = VocalCommand(
                    name=pattern.name,
                    text=text,
                    intent=pattern.intent,
                    entities=entities
                )

                logger.info(f"Commande reconnue: {pattern.intent} | entités: {entities}")

                # Dispatch vers les handlers globaux
                for handler in self._global_handlers:
                    try:
                        handler(command)
                    except Exception as e:
                        logger.error(f"Erreur handler global: {e}")

                # Dispatch vers le handler spécifique
                if pattern.handler:
                    try:
                        pattern.handler(command)
                    except Exception as e:
                        logger.error(f"Erreur handler '{pattern.name}': {e}")

                return command

        # Commande non reconnue
        logger.info(f"Commande non reconnue: '{processed}'")
        if self._unknown_handler:
            self._unknown_handler(text)
        return None

    def has_wake_word(self, text: str) -> bool:
        """Vérifie si le texte contient le mot de réveil."""
        return self.wake_word in text.lower()

    def get_all_intents(self) -> list[str]:
        """Retourne la liste de tous les intents enregistrés."""
        return [p.intent for p in self._patterns]
