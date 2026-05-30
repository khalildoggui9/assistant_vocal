# 🎙️ Assistant Vocal Intelligent — Vosk + pyttsx3 (100% Gratuit)

Fonctionne **sans carte bancaire, sans compte, sans internet**.

---

## 📦 Ce dont tu as besoin

- Python 3.9 ou plus récent
- Un microphone (intégré ou USB)
- Des hauts-parleurs ou écouteurs

---

## ✅ ÉTAPE 1 — Installer Python

### Windows
1. Va sur https://www.python.org/downloads/
2. Télécharge Python 3.11 ou 3.12
3. ⚠️ Coche **"Add Python to PATH"** avant d'installer
4. Vérifie dans le terminal :
```
python --version
```

### Linux / Raspberry Pi
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

---

## ✅ ÉTAPE 2 — Installer les dépendances système

### Windows
Installe **PortAudio** (requis pour le microphone) :
```
pip install pipwin
pipwin install pyaudio
```

### Linux / Raspberry Pi
```bash
sudo apt install portaudio19-dev python3-pyaudio espeak ffmpeg -y
```

---

## ✅ ÉTAPE 3 — Créer l'environnement virtuel

```bash
# Dans le dossier du projet
cd vocal_assistant_v2

# Créer l'environnement
python -m venv .venv

# Activer l'environnement
# Windows :
.venv\Scripts\activate
# Linux / Mac / RPi :
source .venv/bin/activate
```

---

## ✅ ÉTAPE 4 — Installer les packages Python

```bash
pip install -r requirements.txt
```

Si pyaudio échoue sur Windows :
```bash
pip install pipwin
pipwin install pyaudio
pip install -r requirements.txt
```

---

## ✅ ÉTAPE 5 — Télécharger le modèle Vosk (français)

Le modèle permet la reconnaissance vocale **offline**.

### Option A — Petit modèle (40 MB, recommandé pour RPi)
```bash
# Linux / Mac / RPi
wget https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
unzip vosk-model-small-fr-0.22.zip
mv vosk-model-small-fr-0.22/* model/
```

### Option B — Grand modèle (1.4 GB, meilleure précision)
```bash
wget https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip
unzip vosk-model-fr-0.22.zip
mv vosk-model-fr-0.22/* model/
```

### Windows — téléchargement manuel
1. Va sur https://alphacephei.com/vosk/models
2. Télécharge **vosk-model-small-fr-0.22.zip**
3. Décompresse et copie le contenu dans le dossier `model/`

La structure doit ressembler à :
```
model/
├── am/
├── conf/
├── graph/
├── ivector/
└── README
```

---

## ✅ ÉTAPE 6 — Configurer le projet

Le fichier `.env` est déjà prêt avec les valeurs par défaut.
Tu peux changer le nom de l'assistant ou le mot de réveil :

```env
ASSISTANT_NAME=Aria
ASSISTANT_WAKE_WORD=aria
TTS_RATE=160      # vitesse de parole
TTS_VOLUME=1.0
```

---

## ✅ ÉTAPE 7 — Initialiser la base de données Django

```bash
python manage.py migrate
```

---

## 🚀 LANCEMENT

### Terminal 1 — Moteur vocal
```bash
python core/assistant.py
```

### Terminal 2 — Serveur web (dashboard)
```bash
python manage.py runserver
```

Ouvre ton navigateur sur → **http://localhost:8000**

---

## 🧪 TEST RAPIDE (sans microphone)

Pour tester uniquement le moteur de commandes :
```bash
python test_quick.py
```

Tu peux taper des commandes en texte et voir les intents reconnus.

---

## 🎤 Utilisation

1. Dis **"Aria"** → l'assistant se réveille (LED verte)
2. Dis ta commande → l'assistant répond vocalement

### Commandes disponibles

| Ce que tu dis | Ce que fait l'assistant |
|---|---|
| "Quelle heure est-il ?" | Donne l'heure |
| "Quelle est la date ?" | Donne la date |
| "Météo à Paris" | Info météo |
| "Allume la lumière" | GPIO LED ON (RPi) |
| "Éteins la lumière" | GPIO LED OFF (RPi) |
| "Augmente le volume" | Monte le son |
| "Baisse le volume" | Baisse le son |
| "Minuteur de 5 minutes" | Lance un timer |
| "Joue de la musique" | Lance la musique |
| "Arrête la musique" | Stoppe la musique |
| "Calcule 15 + 27" | Calcule et répond |
| "Au revoir" | Éteint l'assistant |

---

## 🌐 API REST

```bash
# Statut de l'assistant
GET http://localhost:8000/api/status/

# Envoyer une commande en texte
POST http://localhost:8000/api/command/
Body: { "text": "quelle heure est-il" }

# Faire parler l'assistant
POST http://localhost:8000/api/speak/
Body: { "text": "Bonjour le monde" }
```

---

## 🔧 Problèmes fréquents

### "No module named pyaudio"
```bash
# Linux
sudo apt install portaudio19-dev
pip install pyaudio

# Windows
pip install pipwin && pipwin install pyaudio
```

### "Model not found" (Vosk)
Vérifie que le dossier `model/` contient bien les fichiers du modèle.

### Micro non détecté
```bash
# Liste les micros disponibles
python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
```

### pyttsx3 muet sur Linux
```bash
sudo apt install espeak
```

---

## 📁 Structure du projet

```
vocal_assistant_v2/
├── core/
│   ├── assistant.py        ← Orchestrateur principal
│   ├── speech_to_text.py   ← Vosk STT (offline)
│   ├── text_to_speech.py   ← pyttsx3 TTS (offline)
│   └── gpio_controller.py  ← Raspberry Pi GPIO
├── commands/
│   ├── engine.py           ← Reconnaissance commandes
│   └── handlers.py         ← Logique métier
├── api/
│   ├── views.py            ← API REST
│   └── consumers.py        ← WebSocket temps réel
├── templates/
│   └── dashboard.html      ← Interface web
├── model/                  ← Modèle Vosk (à télécharger)
├── .env                    ← Configuration
├── manage.py
├── requirements.txt
└── test_quick.py           ← Test sans microphone
```
