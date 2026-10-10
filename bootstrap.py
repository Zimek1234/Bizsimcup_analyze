"""Windows first-run setup using only Python's standard library."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import venv


def main():
    if sys.version_info[:2] not in {(3, 12), (3, 13)} or sys.maxsize <= 2**32:
        print("Je potreba 64bit Python 3.12 nebo 3.13. Nainstalujte jej z python.org.")
        return 1
    root = Path(__file__).resolve().parent
    os.chdir(root)
    env = root / ".venv"
    executable = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.exists():
        print("Vytvarim lokalni virtualni prostredi...")
        venv.EnvBuilder(with_pip=True).create(env)
    requirements = root / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = env / "erpsim-requirements.sha256"
    if not stamp.exists() or stamp.read_text().strip() != digest:
        print("Instaluji zavislosti (prvni spusteni vyzaduje internet)...")
        subprocess.run([str(executable), "-m", "pip", "install", "--disable-pip-version-check",
                        "-r", str(requirements)], check=True)
        stamp.write_text(digest)
    print("Spoustim analytiku. Ukonceni: Ctrl+C v tomto okne.")
    return subprocess.call([str(executable), "-m", "streamlit", "run", str(root / "app.py"),
                            "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=false",
                            "--browser.gatherUsageStats=false"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print("Instalace selhala. Overte internet a opravneni; podrobnosti jsou vyse.")
        raise SystemExit(e.returncode)
