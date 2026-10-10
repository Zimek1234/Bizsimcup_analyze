"""Load local secrets without shell echo. Environment bindings override .env."""
from pathlib import Path
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'service/.env',override=False)
if len(sys.argv)>1 and sys.argv[1] in ('sync','import') and '--game' not in sys.argv:
    game=os.environ.get('ERPSIM_GAME_ID','')
    if not game:
        print('Nastavte ERPSIM_GAME_ID pro konkrétní hru nebo zadejte --game.');raise SystemExit(1)
    sys.argv.extend(['--game',game])
from service.cli import main
raise SystemExit(main())
