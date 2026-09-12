"""Atomic local persistence shared by catalog, settings and acquisition results."""
import json
import os
from pathlib import Path
import tempfile


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
