# bank-security-transactional-system

## Overview 
A full stack banking application built with the use of Python/Flask featuring secure authentications, transaction processing, and automated security testsing. 

## Features 
- JWT authentication with bcrpyt password hashing
- Rate limiting on login to prevent brute force attacks
- Transaction state machine (Initiated -> Validated -> Authorized -> Settled)
- Idempotency keys to prevent duplicate transactions
- Fraud detection rules
- Automated penetration testing script

## Security Testing
This included 'security_test.py' script tests:
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
- nmap('brew install nmap')

### Setup
1. Create and activate a virtual environment: '''bash, python3 -m venv venv
   source venv/bin/activate

2. Install dependencies:
   '''bash, pip install flask, flask-cors, bcrypt, pyjwt, flask-limiter, requests

3. Start the Flask server:
   '''bash, python3 bank_v2.py

4. Open 'gui2.html' in your browser to use the application.

### Running Security Tests
In a second terminal (with venv activated): '''bash, source venv/bin/activate, python3 security_test.py

Results are saved to 'audit_log.txt' with timestamps.
