"""
test_quick.py — Teste le projet SANS microphone ni modèle Vosk.
Lance avec : python test_quick.py
"""
import os, sys
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from commands.engine import CommandEngine

print("\n" + "="*55)
print("  TEST MOTEUR DE COMMANDES — Assistant Vocal Aria")
print("="*55)

engine = CommandEngine(wake_word="aria")

tests = [
    ("quelle heure est-il ?",       "query.time"),
    ("aria quelle heure est-il",    "query.time"),
    ("quel jour sommes-nous ?",     "query.date"),
    ("allume la lumière",           "control.light.on"),
    ("éteins la lumière",           "control.light.off"),
    ("augmente le volume",          "control.volume.up"),
    ("plus fort",                   "control.volume.up"),
    ("baisse le volume",            "control.volume.down"),
    ("quel temps fait-il ?",        "query.weather"),
    ("météo à Paris",               "query.weather"),
    ("calcule 10 + 5",              "utility.calculate"),
    ("mets la musique",             "media.music.play"),
    ("arrête la musique",           "media.music.stop"),
    ("minuteur de 5 minutes",       "utility.timer"),
    ("au revoir",                   "system.shutdown"),
    ("phrase inconnue xyz",         None),
]

passed = 0
for text, expected in tests:
    cmd = engine.process(text)
    got = cmd.intent if cmd else None
    ok  = got == expected
    if ok:
        passed += 1
    status = "✓" if ok else "✗"
    label  = expected or "None"
    print(f"  {status}  [{label:<30}]  \"{text}\"")

print("="*55)
print(f"  Résultat : {passed}/{len(tests)} tests passés")
print("="*55 + "\n")

# Mode interactif
print("Mode interactif — tapez une commande (Ctrl+C pour quitter):\n")
try:
    while True:
        text = input("  Commande > ").strip()
        if not text:
            continue
        cmd = engine.process(text)
        if cmd:
            print(f"  ✓ Intent   : {cmd.intent}")
            print(f"    Entités  : {cmd.entities or '(aucune)'}")
        else:
            print("  ✗ Commande non reconnue")
        print()
except KeyboardInterrupt:
    print("\n  Au revoir !")
