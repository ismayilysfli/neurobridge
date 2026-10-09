"""Optional fresh-browser verification. Install playwright; uses existing Google Chrome."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from agent.report import now
from agent.config import ROOT

parser = argparse.ArgumentParser()
parser.add_argument('--url', required=True, help='The owned Streamlit demo URL')
parser.add_argument('--live-action', action='store_true', help='Consume one real model call in a fresh secure session')
args = parser.parse_args()
reports = ROOT / 'reports'
result = {'tested_at': now(), 'public_url': args.url, 'fresh_browser': True, 'durable_hosting': False,
          'limitation': 'Temporary tunnel requires local processes and host to remain running.'}
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
    page.get_by_role('heading', name='Game Economy Exploit Tester', exact=True).wait_for(timeout=30000)
    page.get_by_text('Public rules and action schemas', exact=True).wait_for()
    assert page.get_by_role('button', name='START AI SECURITY TEST', exact=True).is_enabled()
    assert page.get_by_test_id('stException').count() == 0
    result.update(rules_rendered=True, ai_button_enabled=True)
    print('Fresh public browser renders the application.', flush=True)
    if args.live_action:
        page.get_by_role('combobox').first.click()
        page.get_by_role('option', name='Secure control', exact=True).click()
        actions = page.get_by_role('spinbutton', name='Maximum actions', exact=True)
        actions.fill('1')
        actions.press('Enter')
        page.get_by_role('button', name='START AI SECURITY TEST', exact=True).click()
        page.get_by_role('button', name='DOWNLOAD JSON REPORT', exact=True).wait_for(timeout=120000)
        with page.expect_download(timeout=30000) as download:
            page.get_by_role('button', name='DOWNLOAD JSON REPORT', exact=True).click()
        path = reports / 'browser_live_download.json'
        download.value.save_as(path)
        live = json.loads(path.read_text())
        assert live['executed_actions'] == 1 and live['actions'][0]['status'] == 'ACCEPTED', live['errors']
        assert live['llm_calls'] >= 1 and live['discovery_method'] == 'real_llm'
        result['live_action'] = {'run_id': live['run_id'], 'model': live['model'], 'status': live['status'],
                                 'actions': live['executed_actions'], 'llm_calls': live['llm_calls']}
        print('Actual public-browser AI action and JSON download passed.', flush=True)
    # Select saved genuine evidence explicitly; this does not count as a new discovery.
    evidence = page.get_by_text('Recorded real-model evidence', exact=True)
    evidence.scroll_into_view_if_needed()
    evidence.click()
    selector = page.get_by_role('combobox').last
    selector.wait_for()
    selector.click()
    options = page.get_by_role('option').all()
    match = next(option for option in options if 'reward_reset' in option.inner_text() and 'REPRODUCED' in option.inner_text())
    label = match.inner_text()
    match.click()
    page.wait_for_timeout(1000)
    page.get_by_role('button', name='LOAD RECORDED RUN', exact=True).click()
    page.get_by_text('Recorded real-model run', exact=False).wait_for(timeout=30000)
    page.wait_for_timeout(1000)
    page.get_by_role('button', name='REPLAY FINDING', exact=True).click()
    page.get_by_text('Replay outcome: REPRODUCED', exact=True).wait_for(timeout=30000)
    page.get_by_role('button', name='RUN AGAINST SECURE CONTROL', exact=True).click()
    page.get_by_text('Regression check against secure control: NO_VIOLATION_OBSERVED', exact=True).wait_for(timeout=30000)
    page.wait_for_timeout(1000)
    with page.expect_download(timeout=30000) as download:
        page.get_by_role('button', name='DOWNLOAD JSON REPORT', exact=True).click()
    path = reports / 'browser_download.json'
    download.value.save_as(path)
    report = json.loads(path.read_text())
    assert report['replay']['status'] == 'REPRODUCED'
    assert report['secure_control']['status'] == 'NO_VIOLATION_OBSERVED'
    assert page.get_by_test_id('stException').count() == 0
    page.screenshot(path=str(reports / 'public_demo.png'), full_page=True)
    result.update(loaded_run=label, loaded_run_type='recorded real-model evidence, not a new live discovery',
                  replay_button='REPRODUCED', secure_control_button='NO_VIOLATION_OBSERVED',
                  json_download_valid=True, browser_errors=errors)
    (reports / 'deployment.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    browser.close()
