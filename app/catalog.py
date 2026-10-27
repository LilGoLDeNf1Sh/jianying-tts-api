"""Dynamic voice discovery and account entitlement checks."""
from .errors import VoiceNotFound, VoiceUnavailable

FIELDS = ('name', 'resourceId', 'effectId', 'speakerId', 'supported', 'isVip',
          'isCommercial', 'isLimitFree', 'isClone')


def clean_voice(item):
    return {key: item.get(key) for key in FIELDS}


class VoiceCatalog:
    def __init__(self, bridge_factory, max_voices=2000, page_size=50):
        self.bridge_factory = bridge_factory
        self.max_voices = max_voices
        self.page_size = page_size

    def list_voices(self, query=None):
        query = query.strip() if query else ''
        with self.bridge_factory() as bridge:
            if query:
                return self._search(bridge, query)
            return self._all(bridge)

    def _search(self, bridge, query):
        found = []
        seen = set()
        for offset in range(0, self.max_voices, self.page_size):
            data = bridge._jsb('getToneList', {'keyword': query, 'offset': offset,
                'count': self.page_size, 'includeUnsupported': False})
            resources = data.get('resources')
            if not isinstance(resources, list):
                break
            for item in resources:
                if item.get('isClone') is False:
                    key = item.get('effectId') or item.get('resourceId')
                    if key not in seen:
                        seen.add(key)
                        found.append(clean_voice(item))
            if not data.get('hasMore') or not resources:
                break
        return found

    def _all(self, bridge):
        data = bridge._jsb('getToneCategories', {})
        tabs = data.get('tabs')
        if not isinstance(tabs, list):
            return self._search(bridge, '')
        found, seen = [], set()
        for category in tabs:
            if category.get('available') is False:
                continue
            offset = 0
            while offset < self.max_voices:
                page = bridge._jsb('getToneList', {
                    'categoryId': category.get('id'), 'categoryKey': category.get('key'),
                    'offset': offset, 'count': self.page_size, 'includeUnsupported': False,
                })
                resources = page.get('resources')
                if not isinstance(resources, list) or not resources:
                    break
                for item in resources:
                    if item.get('supported') is False:
                        continue
                    key = item.get('effectId') or item.get('resourceId')
                    if key and key not in seen:
                        seen.add(key)
                        voice = clean_voice(item)
                        voice.update(category_id=category.get('id'),
                                     category_name=category.get('name'))
                        found.append(voice)
                if not page.get('hasMore') or offset + len(resources) >= self.max_voices:
                    break
                offset += len(resources)
        return found

    def resolve(self, voice, bridge):
        candidates = self.list_voices()
        matches = [v for v in candidates
                   if voice in (str(v.get('speakerId')), str(v.get('resourceId')), v.get('name'))]
        if not matches:
            matches = [v for v in self.list_voices(voice) if v.get('name') == voice]
        if not matches:
            raise VoiceNotFound('未找到该音色，请先调用 GET /voices 刷新列表。')
        if len(matches) > 1:
            raise VoiceNotFound('存在同名音色，请改用 speakerId 或 resourceId。')
        selected = matches[0]
        if not selected.get('speakerId') or not selected.get('effectId'):
            raise VoiceNotFound('该音色缺少合成所需参数。')
        if selected.get('supported') is False:
            raise VoiceUnavailable('当前版本不支持该音色。')
        if selected.get('isVip'):
            user = bridge._jsb('getUserSubcriptionInfo', {}).get('user_info', {})
            if not any(user.get(k) for k in ('is_vip', 'is_svip', 'is_ultra')):
                raise VoiceUnavailable('该音色需要会员；当前账号没有可用会员权限。')
        return selected
