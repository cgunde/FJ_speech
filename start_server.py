"""
start_fangstdagbog.py
---------------------
1. Starter whisper_server.py i baggrunden
2. Starter ngrok tunnel på port 5000
3. Henter den nye ngrok URL
4. Opdaterer WHISPER_URL i fangstdagbog.html hvis den er ændret
5. Committer og pusher til GitHub hvis HTML er opdateret

Krav: pip install requests pyngrok
      git skal være installeret og repo konfigureret med push-adgang
"""

import subprocess
import sys
import time
import re
import os
import requests

# ── Parametre ──────────────────────────────────────────────────────
REPO_DIR     = r"C:\Users\Admin\Documents\GitHub\FJ_speech"
HTML_FILE    = os.path.join(REPO_DIR, "fangstdagbog.html")
SERVER_SCRIPT= os.path.join(REPO_DIR, "whisper_server.py")
NGROK_PORT   = 5000
NGROK_API    = "http://127.0.0.1:4040/api/tunnels"
# ──────────────────────────────────────────────────────────────────

def start_whisper():
    print("► Starter Whisper-server…")
    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        creationflags=subprocess.CREATE_NEW_CONSOLE  # eget vindue på Windows
    )
    time.sleep(2)
    print("  Whisper-server startet (PID {})".format(proc.pid))
    return proc

def start_ngrok():
    print("► Starter ngrok…")
    proc = subprocess.Popen(
        ["ngrok", "http", str(NGROK_PORT)],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    # Vent til ngrok API er klar
    for i in range(20):
        time.sleep(1)
        try:
            r = requests.get(NGROK_API, timeout=2)
            if r.status_code == 200:
                tunnels = r.json().get("tunnels", [])
                for t in tunnels:
                    if t.get("proto") == "https":
                        url = t["public_url"]
                        print(f"  ngrok URL: {url}")
                        return proc, url
        except Exception:
            pass
        print(f"  Venter på ngrok… ({i+1}/20)")
    raise RuntimeError("Kunne ikke hente ngrok URL — er ngrok installeret og autentificeret?")

def update_html(new_url):
    endpoint = new_url.rstrip("/") + "/transcribe"
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find eksisterende URL
    pattern = r"(const WHISPER_URL\s*=\s*['\"])https://[^'\"]+(['\"])"
    match = re.search(pattern, content)
    if not match:
        print("  ⚠ Kunne ikke finde WHISPER_URL i HTML-filen")
        return False

    current = match.group(0)
    new_line = f"{match.group(1)}{endpoint}{match.group(2)}"

    if current == new_line:
        print("  HTML er allerede opdateret med korrekt URL — ingen ændring")
        return False

    updated = re.sub(pattern, new_line, content)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"  HTML opdateret: {endpoint}")
    return True

def git_push():
    print("► Committer og pusher til GitHub…")
    cmds = [
        ["git", "-C", REPO_DIR, "add", "fangstdagbog.html"],
        ["git", "-C", REPO_DIR, "commit", "-m", "Auto: opdater ngrok URL"],
        ["git", "-C", REPO_DIR, "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ⚠ Git fejl: {result.stderr.strip()}")
            return
    print("  GitHub opdateret ✓")

def main():
    whisper_proc = start_whisper()
    ngrok_proc, ngrok_url = start_ngrok()
    changed = update_html(ngrok_url)
    if changed:
        git_push()
    else:
        print("► Ingen GitHub-opdatering nødvendig")

    print("\n✓ Alt kører. Luk dette vindue for at stoppe.")
    print(f"  App:    https://cgunde.github.io/FJ_speech/fangstdagbog.html")
    print(f"  Ngrok:  {ngrok_url}")
    print(f"  Dashboard: http://127.0.0.1:4040")
    print("\nTryk Ctrl+C for at afslutte begge servere…")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nAfslutter…")
        whisper_proc.terminate()
        ngrok_proc.terminate()

if __name__ == "__main__":
    main()