from unittest.mock import patch
from contextlib import contextmanager
import json
import pytest

from app.synthesizer import Synthesizer, validate_mp3
from app.errors import UpstreamError


def test_mp3_validation():
    assert validate_mp3(b'ID3\x04')
    assert validate_mp3(b'\xff\xfb\x90\x64')
    with pytest.raises(UpstreamError):
        validate_mp3(b'<html></html>')


class FakeBridge:
    def __init__(self):
        self.calls = 0

    def service_request(self, path, body):
        if path.endswith('/new'):
            return {'tasks': [{'id': 'task-id', 'token': 'task-token'}]}
        self.calls += 1
        if self.calls == 1:
            return {'tasks': [{'status': 'processing'}]}
        return {'tasks': [{'status': 'succeed', 'result': json.dumps({'media': {'url': 'https://media.example.com/audio.mp3'}})}]}


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return b'ID3\x04test'


class Opener:
    def open(self, url, timeout):
        assert url == 'https://media.example.com/audio.mp3'
        return Response()


def test_synthesizes_polls_and_saves_uuid_mp3(tmp_path):
    bridge = FakeBridge()
    @contextmanager
    def factory():
        yield bridge
    class Catalog:
        def resolve(self, voice, bridge):
            return {'speakerId': 'speaker', 'effectId': 'effect', 'name': voice}
    with patch('app.synthesizer.build_opener', return_value=Opener()):
        output, voice = Synthesizer(factory, Catalog(), tmp_path, poll_interval=0).synthesize('你好', '测试')
    assert output.parent == tmp_path
    assert len(output.stem) == 32
    assert output.read_bytes().startswith(b'ID3')
    assert voice['name'] == '测试'
