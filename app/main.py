import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .bridge import JianyingBridge
from .catalog import VoiceCatalog
from .errors import TTSError, VoiceNotFound, VoiceUnavailable, BridgeUnavailable
from .synthesizer import Synthesizer

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = Path(os.getenv('JY_OUTPUT_ROOT', ROOT / 'output')).resolve()
app = FastAPI(title='剪映配音接口', version='1.0.0', docs_url='/docs')
bridge_factory = JianyingBridge
catalog = VoiceCatalog(bridge_factory)
synthesizer = Synthesizer(bridge_factory, catalog, OUTPUT)
_cache = {'expires': 0, 'voices': []}
_cache_lock = threading.Lock()


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=120)
    voice: str = Field(min_length=1, max_length=100)


@app.get('/health')
def health():
    return {'ok': True, 'bridge_ready': JianyingBridge().discovery_path.is_file()}


@app.get('/voices')
def voices(query: str = Query(default='', max_length=100), refresh: bool = False):
    try:
        if query or refresh or time.monotonic() >= _cache['expires']:
            result = catalog.list_voices(query)
            if not query:
                with _cache_lock:
                    _cache.update(voices=result, expires=time.monotonic() + 300)
        else:
            result = _cache['voices']
        return {'count': len(result), 'voices': result}
    except TTSError as error:
        raise HTTPException(503, str(error)) from error


@app.post('/tts')
def tts(request: TTSRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(422, '文本不能只有空白字符。')
    try:
        output, voice = synthesizer.synthesize(text, request.voice.strip())
        return FileResponse(output, media_type='audio/mpeg', filename=output.name,
            headers={'X-Voice-Name': quote(voice['name']), 'X-Audio-Id': output.stem})
    except VoiceNotFound as error:
        raise HTTPException(404, str(error)) from error
    except VoiceUnavailable as error:
        raise HTTPException(403, str(error)) from error
    except BridgeUnavailable as error:
        raise HTTPException(503, str(error)) from error
    except TTSError as error:
        raise HTTPException(502, str(error)) from error


@app.get('/audio/{file_id}')
def audio(file_id: str):
    if not re.fullmatch(r'[0-9a-f]{32}', file_id):
        raise HTTPException(404, '音频不存在。')
    path = OUTPUT / (file_id + '.mp3')
    if not path.is_file():
        raise HTTPException(404, '音频不存在。')
    return FileResponse(path, media_type='audio/mpeg', filename=path.name)
