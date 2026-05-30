import pyaudio
import json
import struct
from vosk import Model, KaldiRecognizer

DEVICE_INDEX = 1
RATE         = 16000
CHUNK        = 8000

model = Model("model")
rec   = KaldiRecognizer(model, RATE)

pa     = pyaudio.PyAudio()
stream = pa.open(
    format=pyaudio.paInt16,
    channels=2,
    rate=RATE,
    input=True,
    input_device_index=DEVICE_INDEX,
    frames_per_buffer=CHUNK
)
stream.start_stream()

print("=== TEST MICROPHONE ===")
print("Parle fort et clairement pendant 15 secondes...")
print("(dis par exemple : bonjour aria quelle heure est-il)")
print()

for i in range(120):
    raw = stream.read(CHUNK, exception_on_overflow=False)

    # Stereo -> Mono : prendre 1 sample sur 2
    samples = struct.unpack(f"<{len(raw)//2}h", raw)
    mono    = struct.pack(f"<{len(samples)//2}h", *samples[::2])

    if rec.AcceptWaveform(mono):
        result = json.loads(rec.Result())
        text   = result.get("text", "").strip()
        print(f"FINAL   : '{text}'")
    else:
        partial = json.loads(rec.PartialResult())
        text    = partial.get("partial", "").strip()
        if text:
            print(f"Partiel : '{text}'")

stream.stop_stream()
stream.close()
pa.terminate()
print("\nTest terminé.")
