"""HTTP adapter for the owned, loopback-only economy sandbox."""
from __future__ import annotations
from urllib.parse import urlparse
import requests

class SandboxError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class SandboxClient:
    def __init__(self, base_url='http://127.0.0.1:8000', timeout=10):
        parsed = urlparse(base_url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('SANDBOX_API must be an HTTP loopback URL for the owned sandbox.')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('SANDBOX_API must not contain credentials, queries, or fragments.')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session_id = None
    def _request(self, method, path, payload=None):
        try:
            response = requests.request(method, self.base_url + path, json=payload,
                                        timeout=self.timeout, allow_redirects=False)
        except requests.RequestException as exc:
            raise SandboxError(f'Sandbox {type(exc).__name__}; check backend health.') from exc
        if not response.ok or 300 <= response.status_code < 400:
            try:
                detail = response.json().get('detail', 'Request failed')
            except ValueError:
                detail = 'Non-JSON error response'
            raise SandboxError(f'HTTP {response.status_code}: {detail}', response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise SandboxError('Sandbox returned invalid JSON.') from exc
    def health(self):
        return self._request('GET', '/api/health')
    def spec(self):
        return self._request('GET', '/api/spec')
    def reset(self, variant='secure'):
        response = self._request('POST', '/api/sessions', {'variant': variant})
        self.session_id = response['session_id']
        return response
    def _session(self):
        if not self.session_id:
            raise SandboxError('Create a sandbox session before exploration.')
        return self.session_id
    def state(self):
        return self._request('GET', f'/api/sessions/{self._session()}')['state']
    def action(self, name, params=None):
        return self._request('POST', f'/api/sessions/{self._session()}/actions',
                             {'action': name, 'params': params or {}})
    def fresh(self):
        return SandboxClient(self.base_url, self.timeout)
