# bank-security-transactional-system

## Overview
A full stack banking application built with Python/Flask featuring secure authentication, transaction processing, and automated security testing.

## Features
- JWT authentication with bcrypt password hashing
- Rate limiting on login to prevent brute force attacks
- Transaction state machine (Initiated -> Validated -> Authorized -> Settled)
- Idempotency keys to prevent duplicate transactions
- Fraud detection rules
- Automated penetration testing script

## Security Testing
The included `security_test.py` script tests:
- Unauthenticated access prevention
- Rate limiter enforcement
- Invalid token rejection
- Open port scanning via nmap

## Tech Stack
- Python, Flask, SQLite
- JWT, bcrypt, flask-limiter
- HTML/CSS/JavaScript frontend

## How To Run

### Prerequisites
- Python 3
- nmap (`brew install nmap`), only needed for the port-scan test

### Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install flask flask-cors bcrypt pyjwt flask-limiter requests
   ```
3. Start the Flask server (runs on port 5001):
   ```bash
   python3 bank_v2.py
   ```
4. Open `gui2.html` in your browser to use the application.

### Running Security Tests
In a second terminal:
```bash
source venv/bin/activate
python3 security_test.py
```
Results are saved to `clean_audit_log.txt` with timestamps.

To run the full audit automatically (starts Flask, runs the tests, stops Flask):
```bash
./run_audit.sh
```
