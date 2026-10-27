from contextlib import contextmanager
import pytest
from app.catalog import VoiceCatalog
from app.errors import VoiceNotFound, VoiceUnavailable


class FakeBridge:
    def __init__(self, member=False):
        self.member = member

    def _jsb(self, method, params):
        if method == 'getUserSubcriptionInfo':
            return {'user_info': {'is_vip': self.member}}
        if method == 'getToneCategories':
            return {'tabs': [{'id': '1', 'key': 'all', 'name': '全部'}]}
        if params.get('categoryId'):
            if params['offset'] == 0:
                return {'resources': [
                    {'name': '音色甲', 'speakerId': 'speaker-a', 'effectId': 'effect-a', 'resourceId': 'resource-a', 'isClone': False, 'supported': True},
                    {'name': '音色甲', 'speakerId': 'speaker-a', 'effectId': 'effect-a', 'resourceId': 'resource-a', 'isClone': False, 'supported': True},
                    {'name': '普通音色', 'speakerId': 'speaker-c', 'effectId': 'effect-c', 'isClone': False},
                ], 'hasMore': True}
            return {'resources': [{'name': '会员音色', 'speakerId': 'speaker-b', 'effectId': 'effect-b', 'resourceId': 'resource-b', 'isVip': True}], 'hasMore': False}
        if params.get('keyword') == '会员音色':
            return {'resources': [{'name': '会员音色', 'speakerId': 'speaker-b', 'effectId': 'effect-b', 'resourceId': 'resource-b', 'isVip': True, 'isClone': False}], 'hasMore': False}
        return {'resources': [{'name': '普通音色', 'speakerId': 'speaker-c', 'effectId': 'effect-c', 'isClone': False}], 'hasMore': False}


def factory(member=False):
    @contextmanager
    def make():
        yield FakeBridge(member)
    return make


def test_sync_all_categories_deduplicates_and_paginates():
    voices = VoiceCatalog(factory()).list_voices()
    assert [v['name'] for v in voices] == ['音色甲', '普通音色', '会员音色']
    assert voices[0]['category_name'] == '全部'


def test_resolves_by_name_or_speaker_id():
    catalog = VoiceCatalog(factory())
    with factory()() as bridge:
        assert catalog.resolve('普通音色', bridge)['speakerId'] == 'speaker-c'
        assert catalog.resolve('speaker-c', bridge)['name'] == '普通音色'


def test_rejects_vip_voice_for_non_member():
    with factory()() as bridge:
        with pytest.raises(VoiceUnavailable):
            VoiceCatalog(factory()).resolve('会员音色', bridge)


def test_allows_vip_voice_for_member():
    with factory(True)() as bridge:
        assert VoiceCatalog(factory(True)).resolve('会员音色', bridge)['isVip']


def test_rejects_unknown_voice():
    with factory()() as bridge:
        with pytest.raises(VoiceNotFound):
            VoiceCatalog(factory()).resolve('不存在', bridge)
