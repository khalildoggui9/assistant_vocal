"""
Moteur IA avec Groq (Llama 3) — 100% gratuit, sans carte bancaire.
Remplace les règles regex par une vraie IA conversationnelle.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class AIEngine:
    """
    Cerveau de l'assistant — utilise Groq (Llama 3) pour comprendre
    et répondre à n'importe quelle question en français.
    """

    SYSTEM_PROMPT = """Tu es {name}, un assistant vocal intelligent installé sur Raspberry Pi.
Tu réponds TOUJOURS en français, de manière courte et claire (1-3 phrases maximum).
Tu es utile, amical et précis.
Quand on te demande l'heure ou la date, réponds avec l'heure/date actuelle fournie.
N'utilise jamais de markdown, de listes à puces ou de formatage — seulement du texte simple parlé.
Si tu ne sais pas quelque chose, dis-le honnêtement."""

    def __init__(self):
        self.api_key    = settings.GROQ_API_KEY
        self.model      = settings.GROQ_MODEL
        self.name       = settings.ASSISTANT_NAME
        self._client    = None
        self._history   = []  # historique de conversation
        self._max_hist  = 10  # nb de tours à garder en mémoire

        self._setup_client()

    def _setup_client(self):
        if not self.api_key or self.api_key == "your_groq_api_key_here":
            logger.warning("Clé Groq non configurée — mode simulation IA.")
            return
        try:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
            logger.info(f"Groq initialisé — modèle: {self.model}")
        except Exception as e:
            logger.error(f"Erreur init Groq: {e}")

    def ask(self, user_text: str, context: dict = None) -> str:
        """
        Envoie une question à l'IA et retourne la réponse textuelle.
        context: infos supplémentaires (heure, date, etc.)
        """
        if not self._client:
            return self._simulate_response(user_text)

        try:
            # Enrichit le prompt système avec le contexte actuel
            system = self._build_system_prompt(context or {})

            # Ajoute le message utilisateur à l'historique
            self._history.append({"role": "user", "content": user_text})

            # Garde seulement les N derniers tours
            recent = self._history[-self._max_hist:]

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}] + recent,
                max_tokens=200,
                temperature=0.7,
            )

            answer = response.choices[0].message.content.strip()

            # Ajoute la réponse à l'historique
            self._history.append({"role": "assistant", "content": answer})

            logger.info(f"IA → '{answer[:80]}'")
            return answer

        except Exception as e:
            logger.error(f"Erreur Groq: {e}")
            return "Désolé, je n'ai pas pu contacter le service d'intelligence artificielle."

    def _build_system_prompt(self, context: dict) -> str:
        """Construit le prompt système avec contexte temps réel."""
        from datetime import datetime
        now = datetime.now()
        jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
        mois  = ["","janvier","février","mars","avril","mai","juin",
                 "juillet","août","septembre","octobre","novembre","décembre"]

        ctx = (
            f"Heure actuelle: {now.hour}h{now.minute:02d}. "
            f"Date: {jours[now.weekday()]} {now.day} {mois[now.month]} {now.year}."
        )
        if context.get("location"):
            ctx += f" Lieu: {context['location']}."

        return self.SYSTEM_PROMPT.format(name=self.name) + "\n\nContexte: " + ctx

    def _simulate_response(self, text: str) -> str:
        """Réponses de secours si pas de clé Groq."""
        from datetime import datetime
        now = datetime.now()
        t = text.lower()
        if "heure" in t:
            return f"Il est {now.hour} heures {now.minute} minutes."
        if "date" in t or "jour" in t:
            return f"Nous sommes le {now.day} du mois {now.month} {now.year}."
        if "bonjour" in t or "salut" in t:
            return f"Bonjour ! Je suis {self.name}, comment puis-je vous aider ?"
        return "Je suis en mode simulation. Configurez une clé Groq pour activer l'IA."

    def reset_history(self):
        """Efface l'historique de conversation."""
        self._history = []
        logger.info("Historique IA effacé.")

    @property
    def is_available(self) -> bool:
        return self._client is not None
