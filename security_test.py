
import requests
import subprocess
import datetime

BASE_URL = "http://127.0.0.1:5001"
LOG_FILE = "audit_log.txt"

def log(message):
    now = datetime.datetime.now()
    now_format = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_format}] {message}")
    with open("clean_audit_log.txt", "a") as f:
        f.write(f"[{now_format}] {message} \n")
def test_unauthenticated_access():
    try:
        response = requests.get(f"{BASE_URL}/accounts/ja")
        log(f"Status code: {response.status_code}")
        try:
            log(f"Response: {response.json()}")
        except:
            log(f"Response: {response.text}")
        if response.status_code == 401:
            log("PASS - unauthenticated access blocked")
        else:
            log("FAIL - unauthenticated access was not blocked")
    except requests.exceptions.ConnectionError:
        log("ERROR - Could not connect to Flask server. Is it running?")
def test_rate_limiting():
    try:
        for i in range(6):
            response = requests.post(f"{BASE_URL}/login",
                json={"username": "testuser", "password": "wrongpassword"}
            )
            log(f"Attempt {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                log("PASS - rate limiter kicked in")
                return
        log("FAIL - rate limiter did not trigger after 6 attempts")
    except requests.exceptions.ConnectionError:
        log("ERROR - Could not connect to Flask server. Is it running?")

def test_invalid_token():
    try:
        fake_token = "this.is.a.fake.token"
        response = requests.get(f"{BASE_URL}/accounts/testuser",
            headers={"Authorization": fake_token}
        )
        log(f"Status Code: {response.status_code}")
        try:
            log(f"Response: {response.json()}")
        except:
            log(f"Response: {response.text}")
        if response.status_code == 401:
            log("PASS - fake token rejected")
        else:
            log("FAIL - fake token was accepted")
    except requests.exceptions.ConnectionError:
        log("ERROR - Could not connect to Flask server. Is it running?")
def scan_open_ports():
    result = subprocess.run(
        ["nmap", "-sV", "127.0.0.1"], 
        capture_output=True, 
        text=True    
    )
    summary_lines = [line for line in result.stdout.split('\n')
                     if any(word in line for word in ['open', 'filtered', 'Nmap done', '5001'])]
    for line in summary_lines:
        log(f"NMAP: {line}")

    if "5001" in result.stdout:
        log("WARNING — Flask server visible on port 5001")
    else:
        log("INFO — Port 5001 not detected")


if __name__ == "__main__":
    log("=== Security Audit Started === ")
    scan_open_ports()
    test_unauthenticated_access()
    test_rate_limiting()
    test_invalid_token()
    log("=== Audit Complete ===")