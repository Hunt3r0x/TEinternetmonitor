import requests
import signal
import sys
import argparse
import time
import subprocess

def handle_interrupt(signum, frame):
    print("\n")
    sys.exit(0)

def authenticate(acct_id, password):
    login_url = "https://my.te.eg/echannel/service/besapp/base/rest/busiservice/v1/auth/userAuthenticate"
    login_headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Csrftoken": "",
        "Isselfcare": "true",
        "Channelid": "702"
    }

    login_data = {
        "acctId": f"FBB{acct_id}",
        "password": password,
        "appLocale": "en-US",
        "isSelfcare": "Y",
        "isMobile": "N",
        "recaptchaToken": ""
    }

    session = requests.Session()

    login_response = session.post(login_url, headers=login_headers, json=login_data)

    response_json = login_response.json()
    csrf_token = response_json['body']['token']
    subscriberId = response_json['body']['subscriber']['subscriberId']

    cookies = session.cookies.get_dict()

    return session, csrf_token, subscriberId

def query_data(session, csrf_token, subscriberId, interval, notify):
    query_url = "https://my.te.eg/echannel/service/besapp/base/rest/busiservice/cz/cbs/bb/queryFreeUnit"
    query_headers = {
        "Host": "my.te.eg",
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Csrftoken": csrf_token,
        "Languagecode": "en-US",  
        "Connection": "close",
        "Isselfcare": "true",
        "Channelid": "702"
    }

    while True:
        query_data = {
            "subscriberId": subscriberId
        }

        query_response = session.post(query_url, headers=query_headers, json=query_data)

        if query_response.status_code == 200:
            response_data = query_response.json()
            for item in response_data['body']:
                total = item.get('total', 1)
                remain = item.get('remain', 0)
                used_percentage = round(((total - remain) / total) * 100, 2)
                used = round(total * (used_percentage / 100), 2)
                free_amount = round(remain, 2)
                
                message = f"{used_percentage}%, {remain} GB remaining."
                print(message)
                
                if notify:                
                    subprocess.Popen(['notify', '-silent', '-id', notify], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).communicate(input=message.encode())

        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Script to authenticate and query data.")
    parser.add_argument("--acctId", type=str, help="The account ID", required=True)
    parser.add_argument("--password", type=str, help="The password", required=True)
    parser.add_argument("--notify", "-n", type=str, help="The notify ID")
    parser.add_argument("--interval", type=int, default=4000, help="Interval in seconds between each query")
    args = parser.parse_args()

    acct_id = args.acctId
    password = args.password
    interval = args.interval
    notify = args.notify

    signal.signal(signal.SIGINT, handle_interrupt)

    session, csrf_token, subscriberId = authenticate(acct_id, password)
    query_data(session, csrf_token, subscriberId, interval, notify)

if __name__ == "__main__":
    main()
