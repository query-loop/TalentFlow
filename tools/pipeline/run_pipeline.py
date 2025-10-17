#!/usr/bin/env python3
"""
Run extraction scenarios defined in scenarios.json against the local dev stack.
- Supports local HTML -> backend /api/extract/from-html
- Supports proxy fetch via frontend /proxy/fetch then backend extraction
Outputs saved to tools/pipeline/out/<scenario_id>.json
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from urllib import request, error

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / 'out'
SCENARIO_FILE = ROOT / 'scenarios.json'
BACKEND_BASE = os.environ.get('BACKEND_BASE', 'http://localhost:8080')
FRONTEND_BASE = os.environ.get('FRONTEND_BASE', 'http://localhost:5173')


def http_post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, headers={'content-type': 'application/json'})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            try:
                return json.loads(body)
            except Exception:
                return {'_raw': body}
    except error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {'_error': f'HTTP {e.code}', '_body': body}
    except Exception as e:
        return {'_error': str(e)}


def run_scenario(sc: Dict[str, Any]) -> Dict[str, Any]:
    sid = sc['id']
    mode = sc.get('mode', 'from-html')
    url = sc['url']
    result: Dict[str, Any] = {'id': sid, 'mode': mode, 'steps': []}

    if mode == 'from-html':
        html_file = sc.get('html_file')
        if not html_file:
            return {**result, 'status': 'error', 'error': 'html_file missing for from-html mode'}
        html_path = ROOT / html_file
        if not html_path.exists():
            return {**result, 'status': 'error', 'error': f'html file not found: {html_file}'}
        html = html_path.read_text('utf-8')
        step = {'action': 'backend_extract_from_html'}
        resp = http_post_json(f"{BACKEND_BASE}/api/extract/from-html", {'url': url, 'html': html})
        step['response'] = resp
        result['steps'].append(step)
        if resp.get('success'):
            result['data'] = resp['data']
            result['status'] = 'ok'
        else:
            result['status'] = 'error'
            result['error'] = resp.get('error') or resp.get('_error') or resp
        return result

    elif mode == 'proxy+from-html':
        # Fetch HTML via frontend proxy
        step1 = {'action': 'frontend_proxy_fetch'}
        resp1 = http_post_json(f"{FRONTEND_BASE}/proxy/fetch", {'url': url})
        step1['response'] = resp1
        result['steps'].append(step1)
        html = ''
        if 'html' in resp1:
            html = resp1['html']
        else:
            # capture error and bail
            result['status'] = 'error'
            result['error'] = f"proxy fetch failed: {resp1.get('error') or resp1.get('_error') or resp1}"
            return result
        # Send HTML to backend for extraction
        step2 = {'action': 'backend_extract_from_html'}
        resp2 = http_post_json(f"{BACKEND_BASE}/api/extract/from-html", {'url': url, 'html': html})
        step2['response'] = resp2
        result['steps'].append(step2)
        if resp2.get('success'):
            result['data'] = resp2['data']
            result['status'] = 'ok'
        else:
            result['status'] = 'error'
            result['error'] = resp2.get('error') or resp2.get('_error') or resp2
        return result

    elif mode == 'backend-job':
        step = {'action': 'backend_extract_job'}
        resp = http_post_json(f"{BACKEND_BASE}/api/extract/job", {'url': url})
        step['response'] = resp
        result['steps'].append(step)
        if resp.get('success'):
            result['data'] = resp['data']
            result['status'] = 'ok'
        else:
            result['status'] = 'error'
            result['error'] = resp.get('error') or resp.get('_error') or resp
        return result

    else:
        return {**result, 'status': 'error', 'error': f'unknown mode: {mode}'}


def check_expectations(result: Dict[str, Any], expect: Dict[str, Any]) -> Dict[str, Any]:
    outcome = {k: v for k, v in result.items()}
    outcome['expectations'] = {'passed': [], 'failed': []}
    data = result.get('data') or {}
    def pass_(msg):
        outcome['expectations']['passed'].append(msg)
    def fail_(msg):
        outcome['expectations']['failed'].append(msg)
    if 'title' in expect:
        if data.get('title') == expect['title']:
            pass_('title matches')
        else:
            fail_(f"title expected '{expect['title']}', got '{data.get('title')}'")
    if 'title_contains' in expect:
        tc = str(expect['title_contains'])
        if tc.lower() in (data.get('title') or '').lower():
            pass_('title contains')
        else:
            fail_(f"title does not contain '{tc}'")
    if 'company' in expect:
        if data.get('company') == expect['company']:
            pass_('company matches')
        else:
            fail_(f"company expected '{expect['company']}', got '{data.get('company')}'")
    if 'company_fallback' in expect and not data.get('company'):
        # if missing company, ensure fallback guess exists in warnings or URL
        warnings = (data.get('provenance') or {}).get('warnings') or []
        url = data.get('source_url') or ''
        if expect['company_fallback'].lower() in url.lower() or any(expect['company_fallback'].lower() in w.lower() for w in warnings):
            pass_('company fallback noted')
        else:
            fail_('company fallback not present')
    return outcome


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run extraction scenarios against local dev stack')
    parser.add_argument('--id', help='Run a single scenario by id')
    parser.add_argument('--out', default=str(OUT_DIR), help='Output directory')
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = json.loads(SCENARIO_FILE.read_text('utf-8'))['scenarios']
    selected = [s for s in scenarios if (not args.id or s['id'] == args.id)]
    if not selected:
        print('No scenarios selected', file=sys.stderr)
        sys.exit(1)

    summary = []
    for sc in selected:
        print(f"\n=== Scenario: {sc['id']} — {sc.get('description','')} ===")
        res = run_scenario(sc)
        res_checked = check_expectations(res, sc.get('expect') or {})
        out_path = OUT_DIR / f"{sc['id']}.json"
        out_path.write_text(json.dumps(res_checked, indent=2), encoding='utf-8')
        failed = len(res_checked.get('expectations', {}).get('failed', []))
        status = 'PASS' if res_checked.get('status') == 'ok' and failed == 0 else 'FAIL'
        print(f"Status: {status}")
        if failed:
            for msg in res_checked['expectations']['failed']:
                print(f" - {msg}")
        summary.append({'id': sc['id'], 'status': status})

    # Write summary
    (OUT_DIR / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    # Print compact summary
    print('\nSummary:')
    for s in summary:
        print(f" - {s['id']}: {s['status']}")


if __name__ == '__main__':
    main()
