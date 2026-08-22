from __future__ import annotations
from pathlib import Path
from typing import Any
import json, os, time

def save_checkpoint(path:str|Path,payload:dict[str,Any])->None:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); data=dict(payload); data['checkpoint_saved_at_epoch']=time.time(); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,path)

def load_checkpoint(path:str|Path):
    path=Path(path); return None if not path.exists() else json.loads(path.read_text(encoding='utf-8'))
