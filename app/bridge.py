"""Jianying loopback bridge; credentials remain in memory and are never logged."""
import http.client
import json
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote

from .errors import BridgeUnavailable, UpstreamError


class JianyingBridge:
    def __init__(self, discovery_path=None, timeout=20):
        self.discovery_path = Path(discovery_path) if discovery_path else Path(tempfile.gettempdir()) / 'infinite-canvas-native-bridge.json'
        self.timeout = timeout
        self._session = None
        self._token = None

    def _request(self, method, path, body=None, port=None, token=None):
        port = port or self.port
        token = token or self._token
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=self.timeout)
        try:
            connection.request(method, path,
                body=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
                headers={'x-infinite-canvas-native-token': token,
                         'Content-Type': 'application/json; charset=utf-8'})
            response = connection.getresponse()
            raw = response.read(4 * 1024 * 1024 + 1)
            if response.status != 200:
                raise UpstreamError(f'剪映桥接请求失败（HTTP {response.status}）。')
            if len(raw) > 4 * 1024 * 1024:
                raise UpstreamError('剪映桥接响应超过 4 MiB 上限。')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise UpstreamError('剪映桥接返回格式异常。')
            return result
        except (OSError, http.client.HTTPException) as error:
            raise BridgeUnavailable('无法连接剪映后台，请打开剪映并保持登录。') from error
        except json.JSONDecodeError as error:
            raise UpstreamError('剪映桥接返回的不是有效 JSON。') from error
        finally:
            connection.close()

    def __enter__(self):
        try:
            config = json.loads(self.discovery_path.read_text(encoding='utf-8'))
            self.port = int(config.get('port', 0))
            self._token = config.get('token')
            if not 1 <= self.port <= 65535 or not isinstance(self._token, str) or not self._token:
                raise ValueError('invalid discovery')
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise BridgeUnavailable('剪映后台桥接未就绪，请打开剪映并保持登录。') from error
        health = self._request('GET', '/.infinite-canvas-native-bridge/health')
        if health.get('ok') is not True:
            raise BridgeUnavailable('剪映后台健康检查未通过。')
        created = self._request('POST', '/infinite-canvas/session', {})
        sid = created.get('session_id')
        if not isinstance(sid, str) or not sid:
            raise UpstreamError('剪映未返回会话编号。')
        self._session = '/infinite-canvas/session/' + quote(sid, safe='')
        return self

    def _jsb(self, method, params, allow_generation=False):
        methods = {'getUserSubcriptionInfo', 'getToneCategories', 'getToneList'}
        if allow_generation:
            methods.add('request')
        if method not in methods:
            raise ValueError('Method is not allowed')
        result = self._request('POST', self._session + '/jsb', {'method': method, 'params': params})
        if result.get('code') != 1 or not isinstance(result.get('data'), dict):
            raise UpstreamError('剪映未接受该请求。')
        return result['data']

    def service_request(self, path, body):
        if path not in {'/lv/v1/web/common_task/new', '/lv/v1/web/common_task/query'}:
            raise ValueError('Service route is not allowed')
        result = self._jsb('request', {
            'url': 'https://lv-pc-api.ulikecam.com' + path,
            'method': 'POST', 'needCommonParams': True, 'header_signing': True,
            'header': {'Content-Type': 'application/json'},
            'data': json.dumps(body, ensure_ascii=False),
        }, allow_generation=True)
        encoded = result.get('encodeData')
        if not isinstance(encoded, str):
            raise UpstreamError('剪映未返回编码后的服务响应。')
        try:
            data = json.loads(unquote(encoded))
            response = data.get('response', {})
            if isinstance(response, str):
                response = json.loads(response)
        except (json.JSONDecodeError, TypeError) as error:
            raise UpstreamError('剪映服务响应格式异常。') from error
        if data.get('httpCode') != 200 or str(response.get('ret')) != '0':
            raise UpstreamError('剪映服务拒绝了请求，请检查登录状态和音色权限。')
        if not isinstance(response.get('data'), dict):
            raise UpstreamError('剪映服务响应缺少数据。')
        return response['data']

    def __exit__(self, exc_type, exc, traceback):
        try:
            if self._session:
                self._request('DELETE', self._session)
        finally:
            self._session = None
            self._token = None
