import json
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler
from uuid import uuid4

from .errors import UpstreamError


def validate_mp3(data):
    if not 4 <= len(data) <= 25 * 1024 * 1024:
        raise UpstreamError('音频为空或超过 25 MiB 上限。')
    if not (data.startswith(b'ID3') or (data[0] == 0xff and data[1] & 0xe0 == 0xe0)):
        raise UpstreamError('下载结果不是有效的 MP3 数据。')
    return data


class Synthesizer:
    def __init__(self, bridge_factory, catalog, output_root, timeout=90, poll_interval=3):
        self.bridge_factory = bridge_factory
        self.catalog = catalog
        self.output_root = Path(output_root)
        self.timeout = timeout
        self.poll_interval = poll_interval

    def synthesize(self, text, voice):
        self.output_root.mkdir(parents=True, exist_ok=True)
        with self.bridge_factory() as bridge:
            selected = self.catalog.resolve(voice, bridge)
            cap = {'biz_scene': 'tts', 'model': 'SystemTTS', 'text': text,
                'tone_info': {'tone_speaker': selected['speakerId'],
                              'tone_effect_id': selected['effectId']}}
            created = bridge.service_request('/lv/v1/web/common_task/new', {
                'bind_id': str(uuid4()), 'enter_from': 'pc_canvas',
                'tasks': [{'context': str(uuid4()), 'type': 10000,
                    'req_key': 'pc_canvas_tool', 'task_version': 'v3',
                    'payload': json.dumps({'cap_key': 'pc_canvas_tool_collect', 'cap_json': cap}, ensure_ascii=False)}],
                'request_extra': json.dumps({'generate_id': str(uuid4())}),
            })
            tasks = created.get('tasks') or []
            if not tasks:
                raise UpstreamError('剪映未创建合成任务，请检查音色权限和账户状态。')
            handle = {k: tasks[0].get(k) for k in ('id', 'token')}
            handle.update(req_key='pc_canvas_tool', task_version='v3')
            deadline = time.monotonic() + self.timeout
            while True:
                queried = bridge.service_request('/lv/v1/web/common_task/query', {'tasks': [handle]})
                task = (queried.get('tasks') or [{}])[0]
                state = task.get('status')
                if state == 'succeed':
                    break
                if state not in ('queuing', 'processing'):
                    raise UpstreamError('剪映合成任务失败，请检查文本和音色权限。')
                if time.monotonic() >= deadline:
                    raise UpstreamError('合成超过等待时限；任务可能仍在客户端处理，请勿重复提交。')
                time.sleep(self.poll_interval)
            result = task.get('result', task.get('payload', {}))
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError as error:
                    raise UpstreamError('合成结果格式异常。') from error
            url = result.get('media', {}).get('url', '')
            parts = urlsplit(url)
            if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
                raise UpstreamError('合成结果没有安全的 HTTPS 音频地址。')
        try:
            with build_opener(ProxyHandler({})).open(url, timeout=30) as response:
                audio = validate_mp3(response.read(25 * 1024 * 1024 + 1))
        except UpstreamError:
            raise
        except Exception as error:
            raise UpstreamError('音频下载失败，请检查网络后重试。') from error
        file_id = uuid4().hex
        output = self.output_root / (file_id + '.mp3')
        with output.open('xb') as target:
            target.write(audio)
        return output, selected
