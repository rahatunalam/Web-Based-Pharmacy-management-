import json
import time
import urllib.error
import urllib.request
from datetime import date

from django.conf import settings
from django.http import HttpResponse

# Subscription check: asks the licence server whether this site may run.
# Fails closed: if LICENSE_URL / LICENSE_KEY are missing, the site is blocked.
LICENSE_URL = settings.LICENSE_URL
LICENSE_KEY = settings.LICENSE_KEY
CHECK_EVERY = 600  # seconds between checks

_cache = {'ok': True, 'at': 0.0}


def _licence_ok():
    try:
        with urllib.request.urlopen(f'{LICENSE_URL}/{LICENSE_KEY}', timeout=5) as r:
            data = json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code >= 500           # 404/403/410 → key unknown or revoked
    except (urllib.error.URLError, OSError, ValueError):
        return _cache['ok']            # server unreachable → keep last result
    state = str(data.get('state') or data.get('status') or '').lower()
    suspend_on = data.get('suspendOn')  # 'YYYY-MM-DD': unpaid bill + grace period
    return data.get('active', True) is not False and data.get('valid', True) is not False \
        and state not in ('suspended', 'paused', 'cancelled', 'expired', 'inactive') \
        and not (suspend_on and date.today().isoformat() >= str(suspend_on))


class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/static/'):
            if not (LICENSE_URL and LICENSE_KEY):
                _cache['ok'] = False
            elif time.time() - _cache['at'] > CHECK_EVERY:
                _cache.update(ok=_licence_ok(), at=time.time())
            if not _cache['ok']:
                return HttpResponse(
                    '<h2>Subscription inactive</h2><p>This service is suspended. '
                    'Please contact your provider to renew.</p>', status=402)
        return self.get_response(request)
