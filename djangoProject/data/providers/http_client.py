import requests
from django.conf import settings

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    timeout = getattr(settings, 'EXTERNAL_DATA_TIMEOUT', 25)
    session.request = _wrap_timeout(session.request, timeout)
    proxy = getattr(settings, 'EXTERNAL_HTTP_PROXY', '') or ''
    if proxy:
        session.proxies.update({'http': proxy, 'https': proxy})
    return session


def _wrap_timeout(request_func, timeout):
    def wrapped(method, url, **kwargs):
        kwargs.setdefault('timeout', timeout)
        return request_func(method, url, **kwargs)

    return wrapped
