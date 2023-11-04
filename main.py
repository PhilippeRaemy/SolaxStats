from datetime import datetime
import json
import os

import requests

user_name = os.environ['USER_NAME']
site_password = os.environ['SITE_PASSWORD']
config_password = os.environ['CONFIG_PASSWORD']
encrypted_password = os.environ['ENCRYPTED_PASSWORD']
site_id = os.environ['SITE_ID']


def login(url, proxies) -> requests.Session:
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Connection': 'keep-alive',
        'Content-Length': '81',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host': 'www.solaxcloud.com',
        'Origin': 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest': None,
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang': 'en_US',
        'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    payload = {'username': user_name, 'userpwd': encrypted_password}

    session = requests.Session()
    response = session.post(url, headers=headers, data=payload) #, proxies=proxies, verify=False)
    return session, (json_decode(response))


def json_decode(response):
    json_response = json.loads(response.content.decode('utf8'))
    print(json.dumps(json_response, indent=2))
    return json_response


# Press the green button in the gutter to run the script.
def get_daily_data(session, token, url, date: datetime, proxies):
    payload = {
        'siteId': os.environ['SITE_ID'],
        'time': date.strftime('%Y-%m-%d')
    }
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Connection': 'keep-alive',
        'Content-Length': str(len(payload)),
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host': 'www.solaxcloud.com',
        'Origin': 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang': 'en_US',
        # 'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        # 'sec-ch-ua-mobile': '?0',
        # 'sec-ch-ua-platform': '"Windows"',
        'token': token,
        'version': 'blue',
    }
    print(payload)
    print(json.dumps(headers, indent=2))
    print(len(payload))
    return session.post(url, headers=headers, data=payload) # , proxies=proxies, verify=False)


if __name__ == '__main__':
    http_proxy = "http://127.0.0.1:8888"
    https_proxy = "http://127.0.0.1:8888"

    proxies = {
        "http": http_proxy,
        "https": https_proxy,
    }

    session, session_response = login('https://www.solaxcloud.com/phoebus/login/loginNew', proxies)
    data = get_daily_data(session, session_response.get('token'),
                          'https://www.solaxcloud.com/blue/phoebus/site/getSiteTotalPower',
                          datetime(2023, 11, 3), proxies
                          )
    json_response = json_decode(data)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
