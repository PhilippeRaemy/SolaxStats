import json
import os
import re
import time
import warnings
from datetime import datetime, timedelta
from typing import List
from urllib.parse import parse_qs, urlparse

import pandas as pd

warnings.simplefilter(action='ignore', category=FutureWarning)

import click
import requests

import solax_configure as cfg
import schemas
from clock_watch import clock_watch

LEGACY_LOGIN_URL = 'https://www.solaxcloud.com/phoebus/login/loginNew'
LEGACY_DAILY_URL = 'https://www.solaxcloud.com/blue/phoebus/site/getSiteTotalPower'
WEB_LOGIN_URL = 'https://global.solaxcloud.com/#/login'


@click.group()
@click.version_option()
def cli():
    """Handles solax inverter stats"""


@cli.group()
def extract():
    """Stats retrieval and basic aggregations"""


def login(url, proxies, user_name, encrypted_password) -> requests.Session:
    headers = {
        'Accept'            : 'application/json, text/plain, */*',
        'Accept-Encoding'   : 'gzip, deflate, br',
        'Accept-Language'   : 'en-US,en;q=0.9,fr;q=0.8',
        'Connection'        : 'keep-alive',
        'Content-Length'    : '81',
        'Content-Type'      : 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host'              : 'www.solaxcloud.com',
        'Origin'            : 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest'    : None,
        'Sec-Fetch-Mode'    : 'cors',
        'Sec-Fetch-Site'    : 'same-origin',
        'User-Agent'        : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang'              : 'en_US',
        'sec-ch-ua'         : '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile'  : '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    payload = {'username': user_name, 'userpwd': encrypted_password}

    session = requests.Session()
    response = session.post(url, headers=headers, data=payload)  # , proxies=proxies, verify=False)
    return session, (json_decode(response))


def json_decode(response):
    json_response = json.loads(response.content.decode('utf8'))
    return json_response


def first_non_empty(*values):
    for value in values:
        if value:
            return value
    return None


def fill_first_matching_selector(page, selectors, value):
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.fill(value)
            return True
    return False


def get_login_frames(page):
    frames = [page]
    for frame in page.frames:
        if frame != page.main_frame:
            frames.append(frame)
    return frames


def try_click_login_mode_selectors(frame):
    for selector in [
        'button:has-text("Account")',
        'button:has-text("Password")',
        'text=Account Login',
        'text=Password Login',
        'text=User Name',
    ]:
        locator = frame.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            try:
                locator.first.click(timeout=300)
            except Exception:
                pass


def find_and_fill_login_fields(page, user_name, site_password):
    user_selectors = [
        'input[autocomplete="username"]',
        'input[name="username"]',
        'input[name="userName"]',
        'input[name="account"]',
        'input[name="accountNumber"]',
        'input[id="username"]',
        'input[id="userName"]',
        'input[type="email"]',
        'input[placeholder*="user" i]',
        'input[placeholder*="mail" i]',
        'label:has-text("User Name") + input',
        'label:has-text("Email") + input',
    ]
    password_selectors = [
        'input[type="password"]',
        'input[name="password"]',
        'input[name="pwd"]',
        'input[id="password"]',
        'input[autocomplete="current-password"]',
        'input[placeholder*="password" i]',
        'label:has-text("Password") + input',
    ]

    for _ in range(4):
        for frame in get_login_frames(page):
            try_click_login_mode_selectors(frame)
            username_ok = fill_first_matching_selector(frame, user_selectors, user_name)
            password_ok = fill_first_matching_selector(frame, password_selectors, site_password)
            if username_ok and password_ok:
                return frame
        page.wait_for_timeout(1000)
    return None


def count_visible_inputs(page):
    total = 0
    for frame in get_login_frames(page):
        try:
            locator = frame.locator('input')
            for i in range(locator.count()):
                if locator.nth(i).is_visible():
                    total += 1
        except Exception:
            continue
    return total


def read_token_from_page_storage(page):
    return page.evaluate("""
        () => {
          const directKeys = ['token', 'access_token', 'accessToken'];
          for (const store of [window.sessionStorage, window.localStorage]) {
            for (const key of directKeys) {
              const value = store.getItem(key);
              if (value) return value;
            }
            for (let i = 0; i < store.length; i++) {
              const key = store.key(i);
              const raw = store.getItem(key);
              if (!raw) continue;
              try {
                const parsed = JSON.parse(raw);
                if (parsed && typeof parsed === 'object') {
                  if (parsed.token) return parsed.token;
                  if (parsed.access_token) return parsed.access_token;
                  if (parsed.accessToken) return parsed.accessToken;
                }
              } catch (e) {
              }
            }
          }
          return null;
        }
    """)


def read_token_from_cookies(context):
    for cookie in context.cookies():
        name = (cookie.get('name') or '').lower()
        value = cookie.get('value')
        if value and 'token' in name:
            return value
    return None


def extract_token_from_payload(payload):
    token_keys = {'token', 'access_token', 'accessToken'}
    if isinstance(payload, dict):
        for key in token_keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            found = extract_token_from_payload(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = extract_token_from_payload(item)
            if found:
                return found
    return None


def extract_token_from_authorization(value):
    if not value:
        return None
    if value.lower().startswith('bearer '):
        return value[7:].strip()
    return None


def extract_encrypted_password_from_request(request):
    try:
        parsed = urlparse(request.url)
        query = parse_qs(parsed.query)
        post_data = request.post_data or ''
        body = parse_qs(post_data)

        for source in (body, query):
            # Legacy endpoint payload field.
            userpwd = source.get('userpwd')
            if userpwd and userpwd[0]:
                return userpwd[0]

        # New website flow often sends encrypted request envelope in data=...
        data_param = body.get('data') or query.get('data')
        if data_param and data_param[0]:
            return data_param[0]
    except Exception:
        pass
    return None


def get_api_token_via_browser(user_name, site_password, login_url=None, headless=True, timeout_seconds=120,
                              debug_login=False):
    artifacts = get_auth_artifacts_via_browser(
        user_name=user_name,
        site_password=site_password,
        login_url=login_url,
        headless=headless,
        timeout_seconds=timeout_seconds,
        debug_login=debug_login,
    )
    return artifacts['token']


def get_auth_artifacts_via_browser(user_name, site_password, login_url=None, headless=True, timeout_seconds=120,
                                   debug_login=False):
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as ex:
        raise click.ClickException(
            'Browser auto auth requires playwright. Install it with: pip install playwright; playwright install chromium'
        ) from ex

    target_url = login_url or WEB_LOGIN_URL
    timeout_ms = int(timeout_seconds * 1000)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        captured = {'token': None, 'token_source': None, 'encrypted_password': None, 'password_source': None}

        def set_captured_token(value, source):
            if value and not captured['token']:
                captured['token'] = value
                captured['token_source'] = source

        def set_captured_encrypted_password(value, source):
            if value and not captured['encrypted_password']:
                captured['encrypted_password'] = value
                captured['password_source'] = source

        def on_request(request):
            try:
                headers = request.headers
                set_captured_token(headers.get('token'), 'request-header:token')
                set_captured_token(extract_token_from_authorization(headers.get('authorization')),
                                   'request-header:authorization')
                set_captured_encrypted_password(
                    extract_encrypted_password_from_request(request),
                    f'request-payload:{request.url}'
                )
            except Exception:
                pass

        def on_response(response):
            try:
                body = response.json()
                set_captured_token(extract_token_from_payload(body), f'response-json:{response.url}')
            except Exception:
                pass

        page.on('request', on_request)
        page.on('response', on_response)

        try:
            page.goto(target_url, wait_until='domcontentloaded', timeout=timeout_ms)

            login_frame = find_and_fill_login_fields(page, user_name, site_password)
            if not login_frame:
                visible_input_count = count_visible_inputs(page)
                if debug_login:
                    click.echo(f'DEBUG login url: {page.url}')
                    click.echo(f'DEBUG frames: {len(page.frames)}')
                    click.echo(f'DEBUG visible inputs: {visible_input_count}')
                raise click.ClickException(
                    f'Could not find username/password fields on login page (visible inputs: {visible_input_count}).'
                )

            clicked = False
            for selector in [
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button[type="submit"]',
                'input[type="submit"]',
            ]:
                locator = login_frame.locator(selector)
                if locator.count() > 0 and locator.first.is_visible():
                    locator.first.click()
                    clicked = True
                    break

            if not clicked:
                login_frame.keyboard.press('Enter')

            end_time = time.time() + timeout_seconds
            while time.time() < end_time and not captured['token']:
                if page.is_closed():
                    break

                try:
                    token = read_token_from_page_storage(page)
                    if token:
                        set_captured_token(token, 'storage')
                except Exception:
                    if page.is_closed():
                        break

                cookie_token = read_token_from_cookies(context)
                if cookie_token:
                    set_captured_token(cookie_token, 'cookie')

                if captured['token']:
                    break
                time.sleep(1)

            if not captured['token']:
                if page.is_closed():
                    raise click.ClickException(
                        'Browser closed before token was captured. Keep it open a few more seconds after landing page.'
                    )
                raise click.ClickException(
                    'Could not retrieve token from browser storage. Complete any MFA/captcha and try again with --no-headless.'
                )

            if debug_login:
                click.echo(f'DEBUG token source: {captured["token_source"]}')
                if captured['encrypted_password']:
                    click.echo(f'DEBUG encrypted password source: {captured["password_source"]}')

            return {
                'token': captured['token'],
                'encrypted_password': captured['encrypted_password']
            }
        except PlaywrightTimeoutError as ex:
            raise click.ClickException(f'Browser login timed out after {timeout_seconds}s.') from ex
        finally:
            context.close()
            browser.close()


def save_auth_to_config(token=None, encrypted_password=None):
    local_file = getattr(cfg, 'local_file', None)
    if not local_file:
        raise click.ClickException('No config file path available in current configuration.')

    config = {}
    if os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf8') as fi:
            content = fi.read().strip()
            if content:
                config = json.loads(content)

    if token:
        config['api_token'] = token
    if encrypted_password:
        config['encrypted_password'] = encrypted_password
    os.makedirs(os.path.dirname(local_file), exist_ok=True)
    with open(local_file, 'w', encoding='utf8') as fi:
        json.dump(config, fi, indent=2)

    if token:
        setattr(cfg, 'api_token', token)
    if encrypted_password:
        setattr(cfg, 'encrypted_password', encrypted_password)


def is_auth_failure(response, payload):
    if getattr(response, 'status_code', None) in (401, 403):
        return True
    if not isinstance(payload, dict):
        return True

    text = json.dumps(payload).lower()
    auth_markers = ['invalid token', 'token invalid', 'token expired', 'unauthorized', 'login']
    return any(marker in text for marker in auth_markers)


def token_works_for_daily_data(session, token, probe_date, proxies):
    response = get_daily_data(session, token, LEGACY_DAILY_URL, probe_date, proxies)
    try:
        payload = json_decode(response)
    except Exception:
        return False
    return not is_auth_failure(response, payload)


def resolve_session_token_with_fallback(proxies, user_name, site_password, encrypted_password, api_token,
                                        browser_headless, login_url, timeout_seconds, debug_login,
                                        probe_date=None):
    resolved_user_name = first_non_empty(user_name, getattr(cfg, 'user_name', None))
    resolved_site_password = first_non_empty(site_password, getattr(cfg, 'site_password', None))
    resolved_encrypted_password = first_non_empty(encrypted_password, getattr(cfg, 'encrypted_password', None))
    resolved_api_token = first_non_empty(api_token, getattr(cfg, 'api_token', None))
    resolved_login_url = first_non_empty(login_url, getattr(cfg, 'solax_login_url', None), WEB_LOGIN_URL)
    check_date = probe_date or datetime.now()

    # 1) Try saved token first.
    if resolved_api_token:
        token_session = requests.Session()
        if token_works_for_daily_data(token_session, resolved_api_token, check_date, proxies):
            return token_session, resolved_api_token

    # 2) Try encrypted password login next.
    if resolved_user_name and resolved_encrypted_password:
        session, session_response = login(LEGACY_LOGIN_URL, proxies, resolved_user_name, resolved_encrypted_password)
        token = session_response.get('token')
        if token and token_works_for_daily_data(session, token, check_date, proxies):
            save_auth_to_config(token=token)
            return session, token

    # 3) Last fallback: browser interaction with plain password.
    if not resolved_user_name:
        raise click.ClickException('Missing username. Provide --user-name or USER_NAME/SOLAX_USER_NAME.')
    if not resolved_site_password:
        raise click.ClickException('Missing password. Provide --site-password or SITE_PASSWORD/SOLAX_SITE_PASSWORD.')

    artifacts = get_auth_artifacts_via_browser(
        user_name=resolved_user_name,
        site_password=resolved_site_password,
        login_url=resolved_login_url,
        headless=browser_headless,
        timeout_seconds=timeout_seconds,
        debug_login=debug_login,
    )
    token = artifacts.get('token')
    discovered_encrypted_password = artifacts.get('encrypted_password')
    if not token:
        raise click.ClickException('Browser auth did not return a token.')

    token_session = requests.Session()
    if not token_works_for_daily_data(token_session, token, check_date, proxies):
        raise click.ClickException('Received token from browser login, but it failed daily data authorization check.')

    save_auth_to_config(token=token, encrypted_password=discovered_encrypted_password)
    return token_session, token


def resolve_session_token(proxies, auth_mode=None, user_name=None, site_password=None,
                          encrypted_password=None, api_token=None, browser_headless=True,
                          login_url=None, timeout_seconds=120, debug_login=False, probe_date=None):
    mode = (first_non_empty(auth_mode, getattr(cfg, 'auth_mode', None), 'auto') or '').lower()
    resolved_user_name = first_non_empty(user_name, getattr(cfg, 'user_name', None))
    resolved_site_password = first_non_empty(site_password, getattr(cfg, 'site_password', None))
    resolved_encrypted_password = first_non_empty(encrypted_password, getattr(cfg, 'encrypted_password', None))
    resolved_api_token = first_non_empty(api_token, getattr(cfg, 'api_token', None))
    resolved_login_url = first_non_empty(login_url, getattr(cfg, 'solax_login_url', None), WEB_LOGIN_URL)

    if mode in ('auto', 'fallback'):
        return resolve_session_token_with_fallback(
            proxies=proxies,
            user_name=resolved_user_name,
            site_password=resolved_site_password,
            encrypted_password=resolved_encrypted_password,
            api_token=resolved_api_token,
            browser_headless=browser_headless,
            login_url=resolved_login_url,
            timeout_seconds=timeout_seconds,
            debug_login=debug_login,
            probe_date=probe_date,
        )

    if mode in ('token', 'api_token'):
        if not resolved_api_token:
            raise click.ClickException('Auth mode token requires --api-token or SOLAX_API_TOKEN.')
        return requests.Session(), resolved_api_token

    if mode in ('legacy_encrypted', 'encrypted_login', 'legacy'):
        if not resolved_user_name:
            raise click.ClickException('Missing username. Provide --user-name or USER_NAME/SOLAX_USER_NAME.')

        # Backward compatibility: if encrypted password is missing, allow site_password as a fallback.
        login_password = first_non_empty(resolved_encrypted_password, resolved_site_password)
        if not login_password:
            raise click.ClickException(
                'Missing password. Provide --encrypted-password, --site-password, ENCRYPTED_PASSWORD, or SITE_PASSWORD.'
            )

        session, session_response = login(LEGACY_LOGIN_URL, proxies, resolved_user_name, login_password)
        token = session_response.get('token')
        if not token:
            raise click.ClickException(
                f'Login failed. No token returned. Response: {session_response}')
        return session, token

    if mode in ('browser_auto', 'web_auto'):
        if not resolved_user_name:
            raise click.ClickException('Missing username. Provide --user-name or USER_NAME/SOLAX_USER_NAME.')
        if not resolved_site_password:
            raise click.ClickException('Missing password. Provide --site-password or SITE_PASSWORD/SOLAX_SITE_PASSWORD.')

        token = get_api_token_via_browser(
            user_name=resolved_user_name,
            site_password=resolved_site_password,
            login_url=resolved_login_url,
            headless=browser_headless,
            timeout_seconds=timeout_seconds,
            debug_login=debug_login,
        )
        return requests.Session(), token

    raise click.ClickException(f'Unsupported auth mode "{mode}".')


# Press the green button in the gutter to run the script.
def get_daily_data(session, token, url, date: datetime, proxies):
    payload = {
        'siteId': cfg.site_id,
        'time'  : date.strftime('%Y-%m-%d')
    }
    headers = {
        'Accept'            : 'application/json, text/plain, */*',
        'Accept-Encoding'   : 'gzip, deflate, br',
        'Accept-Language'   : 'en-US,en;q=0.9,fr;q=0.8',
        'Connection'        : 'keep-alive',
        'Content-Length'    : str(len(payload)),
        'Content-Type'      : 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host'              : 'www.solaxcloud.com',
        'Origin'            : 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest'    : 'empty',
        'Sec-Fetch-Mode'    : 'cors',
        'Sec-Fetch-Site'    : 'same-origin',
        'User-Agent'        : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang'              : 'en_US',
        'sec-ch-ua'         : '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile'  : '?0',
        'sec-ch-ua-platform': '"Windows"',
        'token'             : token,
        'version'           : 'blue',
    }
    # print(payload)
    # print(json.dumps(headers, indent=2))
    # print(len(payload))
    return session.post(url, headers=headers, data=payload)  # , proxies=proxies, verify=False)


@extract.command('history')
@click.option('--auth-mode',
              type=click.Choice(['auto', 'legacy_encrypted', 'token', 'browser_auto'], case_sensitive=False),
              required=False,
              default=None,
              help='Authentication mode. Defaults to config or auto fallback chain.')
@click.option('--user-name', required=False, default=None, help='SolaX username override.')
@click.option('--site-password', required=False, default=None, help='SolaX password override.')
@click.option('--encrypted-password', required=False, default=None,
              help='Pre-encrypted SolaX password override for legacy login endpoint.')
@click.option('--api-token', required=False, default=None, help='Direct API token override.')
@click.option('--browser-headless/--no-browser-headless', default=True,
              help='For browser_auto mode, run browser in headless mode (disable for MFA/captcha).')
@click.option('--login-url', required=False, default=None, help='Browser login URL override.')
@click.option('--timeout-seconds', required=False, default=120, type=int,
              help='Browser login timeout for browser_auto mode.')
@click.option('--debug-login', is_flag=True, default=False,
              help='Print login-page diagnostics if browser_auto field discovery fails.')
def extract_history(auth_mode, user_name, site_password, encrypted_password, api_token, browser_headless,
                    login_url, timeout_seconds, debug_login):
    with clock_watch(print, f'Download history') as cw:
        # fiddler proxy
        http_proxy = "http://127.0.0.1:8888"
        https_proxy = "http://127.0.0.1:8888"

        proxies = {
            "http" : http_proxy,
            "https": https_proxy,
        }

        try:
            with open(cfg.local_file, 'r') as stats_file:
                stats = json.loads(stats_file.read())
        except Exception as ex:
            print(ex)
            stats = []

        solax_rawdata_folder = cfg.solax_rawdata_folder
        os.makedirs(cfg.solax_stats_folder, exist_ok=True)
        os.makedirs(solax_rawdata_folder, exist_ok=True)
        target_file = cfg.solax_stats_file
        target_file_pattern = cfg.re_json

        try:
            last_json_datetime = max(cfg.date_from_filename(fi)
                                     for fi in os.listdir(solax_rawdata_folder)
                                     if cfg.re_json.match(fi))
        except:
            last_json_datetime = datetime.strptime('2023-09-01', '%Y-%m-%d')

        session, token = resolve_session_token(
            proxies=proxies,
            auth_mode=auth_mode,
            user_name=user_name,
            site_password=site_password,
            encrypted_password=encrypted_password,
            api_token=api_token,
            browser_headless=browser_headless,
            login_url=login_url,
            timeout_seconds=timeout_seconds,
            debug_login=debug_login,
            probe_date=last_json_datetime,
        )
        while last_json_datetime < datetime.now():
            data = get_daily_data(session, token,
                                  LEGACY_DAILY_URL,
                                  last_json_datetime, proxies
                                  )
            json_response = json_decode(data)

            if is_auth_failure(data, json_response):
                session, token = resolve_session_token(
                    proxies=proxies,
                    auth_mode='auto',
                    user_name=user_name,
                    site_password=site_password,
                    encrypted_password=encrypted_password,
                    api_token=token,
                    browser_headless=browser_headless,
                    login_url=login_url,
                    timeout_seconds=timeout_seconds,
                    debug_login=debug_login,
                    probe_date=last_json_datetime,
                )
                data = get_daily_data(session, token,
                                      LEGACY_DAILY_URL,
                                      last_json_datetime, proxies
                                      )
                json_response = json_decode(data)
                if is_auth_failure(data, json_response):
                    raise click.ClickException(f'Authentication failed after refresh on {last_json_datetime:%Y-%m-%d}.')

            json_file = os.path.join(solax_rawdata_folder, cfg.gen_json_d(last_json_datetime))
            with open(json_file, 'w') as fi:
                fi.write(json.dumps(json_response, indent=2))

            json_to_feather(json_file, json_response.get('object'))
            df: pd.DataFrame = pd.DataFrame(json_response.get('object'))

            last_json_datetime += timedelta(days=1)
            cw.print(f'Done {json_file}')
    _aggregate_all()


@extract.command('token-auto')
@click.option('--user-name', required=False, default=None, help='SolaX username override.')
@click.option('--site-password', required=False, default=None, help='SolaX password override.')
@click.option('--login-url', required=False, default=None, help='Browser login URL override.')
@click.option('--headless/--no-headless', default=True,
              help='Run browser in headless mode (disable for MFA/captcha).')
@click.option('--timeout-seconds', required=False, default=120, type=int,
              help='Browser login timeout in seconds.')
@click.option('--debug-login', is_flag=True, default=False,
              help='Print login-page diagnostics if field discovery fails.')
@click.option('--save-config', is_flag=True, default=False,
              help='Persist token and discovered encrypted password in local config file.')
def token_auto(user_name, site_password, login_url, headless, timeout_seconds, debug_login, save_config):
    resolved_user_name = first_non_empty(user_name, getattr(cfg, 'user_name', None))
    resolved_site_password = first_non_empty(site_password, getattr(cfg, 'site_password', None))

    if not resolved_user_name:
        raise click.ClickException('Missing username. Provide --user-name or USER_NAME/SOLAX_USER_NAME.')
    if not resolved_site_password:
        raise click.ClickException('Missing password. Provide --site-password or SITE_PASSWORD/SOLAX_SITE_PASSWORD.')

    artifacts = get_auth_artifacts_via_browser(
        user_name=resolved_user_name,
        site_password=resolved_site_password,
        login_url=first_non_empty(login_url, getattr(cfg, 'solax_login_url', None), WEB_LOGIN_URL),
        headless=headless,
        timeout_seconds=timeout_seconds,
        debug_login=debug_login,
    )
    token = artifacts['token']

    if save_config:
        save_auth_to_config(token=token, encrypted_password=artifacts.get('encrypted_password'))

    click.echo(token)


def json_to_feather(json_file, data=None):
    if not data:
        # print(f'read {json_file}')
        with open(json_file, 'r') as fi:
            data = json.loads(fi.read()).get('object')

    df: pd.DataFrame = pd.DataFrame(data)
    date_columns = ['year', 'month', 'day']
    timestamp_columns = date_columns + ['hour', 'minute']
    if [c for c in date_columns if c not in df.columns]:  # any timestamp column missing, happens in early files
        ma = cfg.target_file_pattern.match(json_file)
        for c in date_columns:
            df[c] = ma.groupdict[c]

    df['timestamp'] = pd.to_datetime(df[timestamp_columns])
    df['elapsed_time'] = df['timestamp'].diff().dt.total_seconds().fillna(300)
    for powerColumn in schemas.POWER_SCHEMA.power_columns:
        if powerColumn in df.columns:
            df[powerColumn + 'KWh'] = df[powerColumn] * df['elapsed_time'] / 3.6
        else:
            print("Missing column " + powerColumn)

    feather_file = json_file.replace('.json', '.feather')
    df.to_feather(feather_file)
    # print(f'wrote {feather_file}')


@extract.command('compress')
@click.option('--force', is_flag=True, default=False)
def compress(force):
    count = 0
    for fi in os.listdir(cfg.solax_rawdata_folder):
        if not cfg.re_json.match(fi):
            continue
        json_file = os.path.join(cfg.solax_rawdata_folder, fi)
        feather_file = json_file.replace('.json', '.feather')

        if not force and os.path.exists(feather_file):
            continue
        json_to_feather(json_file)

        count += 1

    print(f'compressed {count} json files into feather')


def concat_impl(dfs: List[pd.DataFrame], grouping: List[str]) -> pd.DataFrame:
    df = (pd.concat((d  # .dropna(axis=1)
                     for d in dfs
                     if not d.empty), ignore_index=True, verify_integrity=False)
          .groupby(grouping)
          .agg({'elapsed_time': 'sum', **{col: 'sum' for col in schemas.ENERGY_SCHEMA.energy_columns}}))
    for col in schemas.ENERGY_SCHEMA.power_columns:
        if col in df.columns:
            df[col] = df['col' + 'KWh'] / df['elapse_time'] * 3.6
    return df


# TODO: match granularities to the analysis granularities...

granularities = ['All', 'Hourly', 'Daily', 'Monthly']
partioning = ['None']  # , 'Monthly', 'Yearly']


@extract.command('aggregate-all')
def aggregate_all():
    _aggregate_all()


def _aggregate_all():
    with clock_watch(print, 'aggregate all') as cw:
        for partition in partioning:
            for granularity in granularities:
                if not (granularity == 'Yearly' and partition == 'Monthly'):
                    cw.print(f'{granularity} by {partition}')
                    _aggregate(granularity, partition)


@extract.command('aggregate')
@click.option('--granularity', '-f', help='Granularity of the aggregation', required=False, default='All',
              type=click.Choice(granularities, case_sensitive=False))
@click.option('--partition', '-f', help='Partitioning of the files', required=False, default='None',
              type=click.Choice(partioning, case_sensitive=False))
@click.option('--force', is_flag=True, default=False)
def aggregate(granularity, partition):
    return _aggregate(granularity, partition)


def _aggregate(granularity, partition):
    with clock_watch(print, f'Aggregating solax raw files by {granularity} ' +
                            ('into one  file' if partition == 'None' else f'in {partition} files.')) as cw:
        if partition == 'None':
            file_namer = cfg.gen_feather_a(granularity)
        elif partition == 'Yearly':
            file_namer = cfg.gen_feather_y(granularity)
        elif partition == 'Monthly':
            file_namer = cfg.gen_feather_m(granularity)
        else:
            raise ValueError(f'Invalid partition {partition}.')

        feather_file_pattern = re.compile(file_namer(None), re.IGNORECASE)

        folder = cfg.solax_stats_folder
        rawdata = cfg.solax_rawdata_folder
        files = os.listdir(rawdata)
        try:
            max_partition = max((fi for fi in files if feather_file_pattern.match(fi)))
        except ValueError:
            max_partition = ''

        if granularity == 'All':
            grouping = ['year', 'month', 'day', 'hour', 'minute']
        elif granularity == 'Hourly':
            grouping = ['year', 'month', 'day', 'hour']
        elif granularity == 'Daily':
            grouping = ['year', 'month', 'day']
        elif granularity == 'Monthly':
            grouping = ['year', 'month']
        elif granularity == 'Yearly':
            if partition == 'Monthly':
                raise ValueError(f'Cannot partition in {partition} for {granularity} granularity.')
            grouping = ['year']
        else:
            raise ValueError(f'Invalid  granularity {granularity}.')

        previous_partition = ''
        current_partition = ''
        dfs: List[pd.DataFrame] = []
        for fi in files:
            ma = cfg.re_feather_d.match(fi)
            if not ma:
                continue
            current_partition = file_namer(fi)
            if current_partition < max_partition:
                continue
            # print(f'read {fi}, current_partition:{current_partition}')
            if previous_partition and (current_partition != previous_partition):
                filename = os.path.join(folder, previous_partition)
                concat_impl(dfs, grouping).to_feather(filename)
                cw.print(f' > saved {filename}')
                dfs = []
            previous_partition = current_partition
            df = pd.read_feather(os.path.join(rawdata, fi))
            dfs.append(df)

        if current_partition:
            filename = os.path.join(folder, current_partition)
            concat_impl(dfs, grouping).to_feather(filename)
            cw.print(f' > saved {filename}')


if __name__ == '__main__':
    click.cli()
