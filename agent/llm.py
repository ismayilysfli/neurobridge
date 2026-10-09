"""Real OpenAI-compatible inference, bounded retries, no simulated fallback."""
from __future__ import annotations
import os
import time
import threading
from urllib.parse import urlparse
import requests
from agent.config import load_environment
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST = {}
class ModelError(RuntimeError):
    pass
class ModelBudgetError(ModelError):
    def __init__(self, message, reason='calls'):
        super().__init__(message)
        self.reason = reason
class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, temperature=None,
                 timeout=None, max_output_tokens=None, max_retries=2, min_request_interval=None):
        load_environment()
        self.base_url = (base_url or os.getenv('LLM_BASE_URL', '')).rstrip('/')
        self.api_key = api_key or os.getenv('LLM_API_KEY', '')
        self.model = model or os.getenv('LLM_MODEL', '')
        missing = [name for name, value in [('LLM_BASE_URL', self.base_url),
                  ('LLM_API_KEY', self.api_key), ('LLM_MODEL', self.model)] if not value]
        if missing:
            raise ModelError('Missing model configuration: ' + ', '.join(missing))
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ModelError('LLM_BASE_URL must be a valid HTTP(S) API base URL without credentials.')
        try:
            self.temperature = float(temperature if temperature is not None else os.getenv('LLM_TEMPERATURE', '0.3'))
            self.timeout = float(timeout if timeout is not None else os.getenv('LLM_TIMEOUT', '30'))
            self.max_output_tokens = int(max_output_tokens or os.getenv('LLM_MAX_OUTPUT_TOKENS', '512'))
            self.min_request_interval = float(min_request_interval if min_request_interval is not None else os.getenv('LLM_MIN_REQUEST_INTERVAL', '0'))
        except ValueError as exc:
            raise ModelError('Model temperature, timeout, and token limit must be numeric.') from exc
        if not 0 <= self.temperature <= 2 or self.timeout <= 0 or self.max_output_tokens <= 0 or self.min_request_interval < 0:
            raise ModelError('Invalid temperature, timeout, or output-token budget.')
        self.max_retries = max_retries
        self.json_mode = True
        self.calls = 0
        self.records = []
        self.reasoning_effort = os.getenv('LLM_REASONING_EFFORT')
    def complete(self, messages, *, max_attempts, deadline):
        payload = {'model': self.model, 'messages': messages, 'temperature': self.temperature,
                   'max_tokens': self.max_output_tokens}
        if self.reasoning_effort:
            payload['reasoning_effort'] = self.reasoning_effort
        retry_count = 0
        last_error = 'Model-call budget exhausted.'
        for _ in range(max_attempts):
            if self.min_request_interval:
                with _REQUEST_LOCK:
                    key = (self.base_url, self.model)
                    delay = max(0, self.min_request_interval - (time.monotonic() - _LAST_REQUEST.get(key, 0)))
                    if delay >= deadline - time.monotonic():
                        raise ModelBudgetError('Insufficient time for the configured model request interval.', 'time')
                    if delay:
                        time.sleep(delay)
                    _LAST_REQUEST[key] = time.monotonic()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModelBudgetError('Exploration wall-clock timeout.', 'time')
            body = dict(payload)
            if self.json_mode:
                body['response_format'] = {'type': 'json_object'}
            self.calls += 1
            started = time.monotonic()
            record = {'call': self.calls, 'messages': messages, 'json_mode': self.json_mode,
                      'usage': {}, 'status': 'error'}
            self.records.append(record)
            try:
                response = requests.post(self.base_url + '/chat/completions', json=body,
                                         headers={'Authorization': 'Bearer ' + self.api_key},
                                         timeout=min(self.timeout, remaining), allow_redirects=False)
                record['http_status'] = response.status_code
                if not response.ok:
                    try:
                        error_body = response.json()
                        if isinstance(error_body, list):
                            error_body = error_body[0] if error_body else {}
                        provider_error = error_body.get('error', {})
                        if isinstance(provider_error, dict):
                            record['provider_error'] = {key: str(provider_error[key]).replace(self.api_key, '[REDACTED]')[:500]
                                                        for key in ('code', 'status', 'message') if key in provider_error}
                    except (ValueError, AttributeError, TypeError):
                        pass
                if response.status_code in (400, 422) and self.json_mode:
                    text = response.text.lower()
                    if any(term in text for term in ('response_format', 'json_object', 'json mode')):
                        self.json_mode = False
                        record['error'] = 'Provider does not support JSON mode; retrying prompt-only JSON.'
                        last_error = record['error']
                        continue
                if response.status_code in (408, 429, 500, 502, 503, 504):
                    last_error = f'Provider transient HTTP {response.status_code}.'
                    record['error'] = last_error
                    if retry_count >= self.max_retries:
                        raise ModelError(last_error)
                    retry_count += 1
                    try:
                        wait = float(response.headers.get('Retry-After', retry_count))
                    except ValueError:
                        wait = retry_count
                    try:
                        error_body = response.json()
                        if isinstance(error_body, list):
                            error_body = error_body[0] if error_body else {}
                        details = error_body.get('error', {}).get('details', [])
                        for detail in details:
                            if 'retryDelay' in detail:
                                wait = max(wait, float(str(detail['retryDelay']).rstrip('s')))
                    except (ValueError, TypeError, AttributeError):
                        pass
                    if wait >= deadline - time.monotonic():
                        raise ModelBudgetError('Provider retry delay exceeds the remaining exploration time.', 'provider_wait')
                    time.sleep(min(max(wait, 0), 60, max(0, deadline - time.monotonic())))
                    continue
                if not response.ok or 300 <= response.status_code < 400:
                    raise ModelError(f'Provider HTTP {response.status_code}; check endpoint, credentials, and model.')
                data = response.json()
                record['usage'] = data.get('usage') or {}
                raw = data['choices'][0]['message']['content']
                if not isinstance(raw, str):
                    raise ModelError('Provider response has no text message content.')
                record.update(status='ok', response=raw)
                return raw
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = f'Provider {type(exc).__name__}; no model action was returned.'
                record['error'] = last_error
                if retry_count >= self.max_retries:
                    raise ModelError(last_error) from exc
                retry_count += 1
            except requests.RequestException as exc:
                record['error'] = f'Provider {type(exc).__name__}.'
                raise ModelError(record['error']) from exc
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                record['error'] = 'Malformed chat-completion response from provider.'
                raise ModelError(record['error']) from exc
            except ModelError as exc:
                record['error'] = str(exc)
                raise
            finally:
                record['latency_seconds'] = round(time.monotonic() - started, 6)
        raise ModelBudgetError(last_error)
