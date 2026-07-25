from faster_whisper import WhisperModel
from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile, os, json, requests

# ── parametre ──────────────────────────────────────
MODEL_SIZE = "medium"   # tiny / base / small / medium / large
DEVICE     = "cpu"      # skift til "cuda" hvis du har Nvidia GPU
# ──────────────────────────────────────────────────

SPECIES_PROMPT = (
    "Fisketur på dansk. "
    "Lokaliteter: Vedbæk, Skovshoved, Nivå, Faxe. "
    "Arter: sortvels, tangnål, sandart, stribefisk, stribet fløjfisk, havørred, hornfisk, torsk, ål, skrubbe, aborre. "
    "Fisket med: blink, bombarda, gulp, flue, orm, spinneflue. "
    "Eksempler: fanget en havørred på 52 cm fisket med blink i to timer ved Vedbæk, "
    "fisket med gulp efter sandart ved Nivå, nultur ved Skovshoved fisket med bombarda i en time."
)

print("Indlæser Whisper-model…")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type="int8")
print("Klar.")

app = Flask(__name__)
CORS(app, expose_headers=["ngrok-skip-browser-warning"])

@app.after_request
def add_ngrok_header(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "Ingen lydfil"}), 400

    audio = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        audio.save(f.name)
        tmp = f.name

    try:
        segments, _ = model.transcribe(tmp, language="da", initial_prompt=SPECIES_PROMPT)
        tekst = " ".join(s.text.strip() for s in segments)
        return jsonify({"tekst": tekst})
    finally:
        os.remove(tmp)

PARSE_PROMPT = """Du er en fiskeridataassistent. Udtræk følgende fra dikteringen og returner KUN JSON:

{
  "sted": "stednavn eller null",
  "varighed_timer": tal eller null,
  "maalart": "art eller null",
  "fisket_med": "redskab eller null",
  "fangster": [
    {"art": "navn", "laengde_cm": tal eller null, "genuds": true/false}
  ]
}

Returner UDELUKKENDE JSON — ingen forklaring, ingen markdown."""

@app.route("/parse", methods=["POST"])
def parse():
    data = request.get_json()
    if not data or "tekst" not in data:
        return jsonify({"error": "Ingen tekst"}), 400

    tekst = data["tekst"]
    prompt = f"{PARSE_PROMPT}\n\nDiktering: {tekst}"
    prompt_tokens = len(prompt.split())

    print(f"── Parse request ──")
    print(f"  Prompt størrelse: ~{prompt_tokens} ord / ~{len(prompt)} tegn")

    try:
        import time
        t0 = time.time()
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral:7b-instruct",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        elapsed = time.time() - t0
        raw = res.json().get("response", "")
        print(f"  Svartid: {elapsed:.1f}s")
        print(f"  LLM svar: {raw}")
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        parsed["_meta"] = {"prompt_ord": prompt_tokens, "svartid_s": round(elapsed, 1)}
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)