from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.errors import BridgeUnavailable, VoiceNotFound

client = TestClient(app)


def test_health_does_not_expose_bridge_credentials():
    response = client.get('/health')
    assert response.status_code == 200
    assert set(response.json()) == {'ok', 'bridge_ready'}


def test_tts_returns_mp3_and_audio_url_id(tmp_path):
    output = tmp_path / ('a' * 32 + '.mp3')
    output.write_bytes(b'ID3\x04\x00test')
    with patch('app.main.synthesizer.synthesize', return_value=(output, {'name': '测试音色'})):
        response = client.post('/tts', json={'text': '你好', 'voice': '测试音色'})
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'
    assert response.headers['x-audio-id'] == 'a' * 32
    assert response.content.startswith(b'ID3')


def test_tts_rejects_blank_text():
    response = client.post('/tts', json={'text': '  ', 'voice': '测试音色'})
    assert response.status_code == 422


def test_missing_bridge_is_503():
    with patch('app.main.synthesizer.synthesize', side_effect=BridgeUnavailable('请打开剪映')):
        response = client.post('/tts', json={'text': '你好', 'voice': '测试音色'})
    assert response.status_code == 503
    assert 'token' not in response.text.lower()


def test_unknown_voice_is_404():
    with patch('app.main.synthesizer.synthesize', side_effect=VoiceNotFound('未找到')):
        response = client.post('/tts', json={'text': '你好', 'voice': '不存在'})
    assert response.status_code == 404


def test_audio_rejects_path_traversal():
    response = client.get('/audio/..%2Fsecret')
    assert response.status_code == 404
