"""Validate model choices exclusively against public action specifications."""
import json
from copy import deepcopy
from jsonschema import Draft202012Validator
class InvalidChoice(ValueError):
    pass
def parameter_schema(parameters):
    if not isinstance(parameters, dict):
        raise InvalidChoice('Public parameter schema must be an object.')
    if parameters.get('type') == 'object' or 'properties' in parameters:
        schema = deepcopy(parameters)
        schema.setdefault('type', 'object')
        schema.setdefault('additionalProperties', False)
        return schema
    properties = {}
    for name, definition in parameters.items():
        if isinstance(definition, dict):
            properties[name] = deepcopy(definition)
        elif definition in ('string', 'integer', 'number', 'boolean', 'array', 'object'):
            properties[name] = {'type': definition}
        elif isinstance(definition, list):
            properties[name] = {'enum': definition}
        elif isinstance(definition, str) and '|' in definition:
            properties[name] = {'type': 'string', 'enum': [x.strip() for x in definition.split('|')]}
        else:
            properties[name] = {'const': definition}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
def parse_choice(raw, spec):
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith('```') and stripped.endswith('```'):
            stripped = stripped.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        try:
            choice = json.loads(stripped)
        except (ValueError, TypeError) as exc:
            raise InvalidChoice('Model output is not valid JSON.') from exc
    else:
        choice = raw
    if not isinstance(choice, dict):
        raise InvalidChoice('Model output must be a JSON object.')
    if choice.get('stop') is True:
        if set(choice) != {'stop', 'reason'} or not isinstance(choice.get('reason'), str):
            raise InvalidChoice('Stop output requires only stop=true and a reason string.')
        return choice
    if set(choice) != {'action', 'params', 'reason'}:
        raise InvalidChoice('Output must contain exactly action, params, and reason.')
    if not isinstance(choice['action'], str) or not isinstance(choice['reason'], str) or not choice['reason'].strip():
        raise InvalidChoice('Action and nonempty reason must be strings.')
    actions = {a['name']: a for a in spec['actions']}
    if choice['action'] not in actions:
        raise InvalidChoice('Unknown action; use the public action names.')
    schema = parameter_schema(actions[choice['action']].get('parameters', {}))
    errors = sorted(Draft202012Validator(schema).iter_errors(choice['params']), key=lambda e: str(e.path))
    if errors:
        raise InvalidChoice('Invalid action parameters: ' + errors[0].message)
    return deepcopy(choice)
