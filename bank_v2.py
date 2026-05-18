# /// bank_v2
# requires-python = ">=X.XX" TODO: Update this to the minimum Python version you want to support
# dependencies = [
#   TODO: Add any dependencies your script requires
# ]
# ///

# TODO: Update the main function to your needs or remove it.

import sqlite3
from enum import Enum
from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
import bcrypt
import jwt
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback_for_dev_only")
limiter = Limiter(get_remote_address, app=app, default_limits=[])

class TransactionState(Enum):
    INITIATED = "Initiated"
    VALIDATING = "Validating"
    AUTHORIZED = "Authorized"
    PROCESSING = "Processing"
    SETTLED = "Settled"
    FAILED = "Failed"
    REJECTED = "Rejected"
    ROLLED_BACK = "Rolled_Back"

class Transaction:
    def __init__(self, id, idempotency_key, sender_id, receiver_id, amount_cents):
        self.id = id
        self.idempotency_key = idempotency_key
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount_cents = amount_cents
        self.state = TransactionState.INITIATED
        self.failure_reason = None
        self.fee_cents = 0
        self.total_cents = 0
        self.currency = "USD"

    def calculate_fee(self, fee_percent):
        self.fee_cents = int(self.amount_cents * fee_percent / 100)
        self.total_cents = self.amount_cents + self.fee_cents
    def __repr__(self):
        return f"[TX {self.id}] {self.sender_id} -> {self.receiver_id} | ${self.amount_cents / 100:.2f} | {self.state.value}"
    
class Account:
    def __init__(self, id, owner_name, initial_balance_cents, currency="USD"):
        self.id = id
        self.owner_name = owner_name
        self.balance_cents = initial_balance_cents
        self.held_cents = 0
        self.currency = currency

    def available_balance(self):
        return self.balance_cents - self.held_cents
    
    def debit(self, amount):
        self.balance_cents -= amount
     
    def credit(self, amount):
        self.balance_cents += amount
     
    def add_hold(self, amount):
        self.held_cents += amount
   
    def release_hold(self, amount):
        self.held_cents -= amount
    

    def __repr__(self):
        return f"{self.owner_name}, {self.available_balance()}, {self.held_cents}"
    
class Store:
    def __init__(self, db_path="bank.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute(""" Create TABLE IF NOT EXISTS accounts (
                                    id TEXT PRIMARY KEY,
                                    owner_name TEXT, 
                                    balance_cents INTEGER,
                                    held_cents INTEGER
                            )
                            """)
        self.conn.commit()
        self.cursor.execute(""" Create TABLE IF NOT EXISTS transactions (
                                    id TEXT PRIMARY KEY,
                                    idempotency_key TEXT, 
                                    sender_id TEXT,
                                    receiver_id TEXT,
                                    amount_cents INTEGER,
                                    state TEXT,
                                    failure_reason TEXT, 
                                    fee_cents INTEGER,
                                    total_cents INTEGER,
                                    currency TEXT
                            )
                            """)
        self.conn.commit()
        self.cursor.execute(""" CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT) """)
    def save_account(self, account):
        self.cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?)", (account.id, account.owner_name, account.balance_cents, account.held_cents))
        self.conn.commit()
    def find_account(self,id):
        self.cursor.execute("SELECT * FROM accounts WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        account = Account(row[0], row[1], row[2])
        account.held_cents = row[3]
        return account
    def save_transaction(self,tx):
        self.cursor.execute("INSERT OR REPLACE INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (tx.id, tx.idempotency_key, tx.sender_id, tx.receiver_id, tx.amount_cents, tx.state.value, tx.failure_reason, tx.fee_cents, tx.total_cents, tx.currency))
        self.conn.commit()
    def find_transactions(self, id):
        self.cursor.execute("SELECT * FROM transactions WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        transaction = Transaction(row[0], row[1], row[2], row[3], row[4])
        transaction.state = TransactionState(row[5])
        transaction.failure_reason = row[6]
        transaction.fee_cents = row[7]
        transaction.total_cents = row[8]
        transaction.currency = row[9]
        return transaction
    def find_by_idempotency(self,key):
        self.cursor.execute("SELECT * FROM transactions WHERE idempotency_key = ?", (key,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        transaction = Transaction(row[0], row[1], row[2], row[3], row[4])
        transaction.state = TransactionState(row[5])
        transaction.failure_reason = row[6]
        transaction.fee_cents = row[7]
        transaction.total_cents = row[8]
        return transaction
    def save_user(self,user):
        self.cursor.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (user.username, user.password_hash))
        self.conn.commit()
    def find_user(self, username):
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        user = User(row[0], row[1])
        return user
        
class Ledger:
    def __init__(self, Store):
        self.store = Store
        
    def hold_funds(self,tx):
        sender = self.store.find_account(tx.sender_id)
        sender.add_hold(tx.total_cents)
        self.store.save_account(sender)    

        
    def transfer_funds(self,tx):
        sender = self.store.find_account(tx.sender_id)
        receiver = self.store.find_account(tx.receiver_id)
        sender.debit(tx.total_cents)
        receiver.credit(tx.amount_cents)
        sender.release_hold(tx.total_cents)
        self.store.save_account(sender)    
        self.store.save_account(receiver)

    def release_hold(self,tx):
        sender = self.store.find_account(tx.sender_id)
        sender.release_hold(tx.total_cents)
        self.store.save_account(sender)    
        

class Engine:
    ALLOWED_TRANSITIONS = {
        TransactionState.INITIATED:   [TransactionState.VALIDATING, TransactionState.REJECTED],
        TransactionState.VALIDATING:  [TransactionState.AUTHORIZED, TransactionState.REJECTED,TransactionState.FAILED ],
         TransactionState.AUTHORIZED:  [TransactionState.PROCESSING, TransactionState.FAILED],
        TransactionState.PROCESSING:  [TransactionState.SETTLED,    TransactionState.FAILED],
     TransactionState.FAILED:      [TransactionState.ROLLED_BACK],
     TransactionState.SETTLED:     [],
     TransactionState.REJECTED:    [],
     TransactionState.ROLLED_BACK: [],
     }
    def __init__(self, Store, Ledger):
            self.store = Store
            self.ledger = Ledger
            self.FEE_PERCENT = 1.5
            self.converter = CurrencyConverter()
            self.fraud_detector = FraudDetector()

    def transition(self, tx, new_state):
        allowed = self.ALLOWED_TRANSITIONS[tx.state]
        if new_state not in allowed:
            raise Exception(f"Invalid transition: {tx.state} -> {new_state}")
        tx.state = new_state
        self.store.save_transaction(tx)
    
    def initiate_transfer(self, idempotency_key, sender_id, receiver_id, amount_cents):
        key = self.store.find_by_idempotency(idempotency_key)
        if key:
            return key
        else:
            tx = Transaction(str(id({})), idempotency_key, sender_id, receiver_id, amount_cents)
            self.store.save_transaction(tx)
            return tx
    def process_transfer(self, tx):
        try:
            self._validate(tx)
            self._authorize(tx)
            self._process(tx)
            self._settle(tx)
        except Exception as e:
            tx.failure_reason = str(e)
            self.transition(tx, TransactionState.FAILED)
            self.ledger.release_hold(tx)
            self.transition(tx, TransactionState.ROLLED_BACK)
    
    def _validate(self, tx):
        self.transition(tx, TransactionState.VALIDATING)
        sender = self.store.find_account(tx.sender_id)
        receiver = self.store.find_account(tx.receiver_id)
        if sender is None:
           raise Exception("Sender not found")
        if receiver is None:
           raise Exception("Receiver not found")
        if tx.amount_cents <= 0:
            raise Exception("Amount must be positive")
        fraud_reason = self.fraud_detector.check(tx, sender)
        if fraud_reason is not None:
            raise Exception(f"Fraud check failed: {fraud_reason}")
        tx.calculate_fee(self.FEE_PERCENT)
        if sender.available_balance() < tx.total_cents:
           raise Exception("Insufficient Funds")
        if sender.currency != tx.currency:
            tx.amount_cents = self.converter.convert(tx.amount_cents, tx.currency, sender.currency)
            tx.currency = sender.currency
            tx.calculate_fee(self.FEE_PERCENT)
        

    def _authorize(self, tx):
        self.transition(tx, TransactionState.AUTHORIZED)
        self.ledger.hold_funds(tx)
    
    def _process(self, tx):
        self.transition(tx, TransactionState.PROCESSING)
        self.ledger.transfer_funds(tx)

    def _settle(self, tx):
         self.transition(tx, TransactionState.SETTLED)

class CurrencyConverter:
    RATES = { ("USD", "EUR") : 0.92, ("EUR", "USD") : 1.09, ("USD", "GBP") : 0.79, ("GBP", "USD") : 1.27, ("USD", "USD") : 1.0, ("EUR", "EUR") : 1.0, ("GBP", "GBP") : 1.0,}
    
    def convert(self, amount_cents, from_currency, to_currency):
        rate = self.RATES.get((from_currency, to_currency))
        if rate is None:
            raise Exception(f"Unsupported conversion: {from_currency} to {to_currency}")
        else:
            return int(amount_cents * rate)
        
class FraudDetector:
    def __init__(self):
        self.rules = [
            self._check_large_transfer,
            self._check_round_number,
            self._check_self_transfer
        ]

    def check(self, tx, sender):
        for rule in self.rules:
            result = rule(tx, sender)
            if result is not None:
                return result
        return None
        
    def _check_large_transfer(self, tx, sender):
        if tx.amount_cents > 1_000_000:
            return "Transfer exceeds $10,000 limit"
        return None
    
    def _check_round_number(self, tx, sender):
        if tx.amount_cents > 1000_000 and tx.amount_cents % 10_000 == 0:
            return "Suspicious Transfer"
        return None

    def _check_self_transfer(self, tx, sender):
        if tx.sender_id == tx.receiver_id:
            return "Suspicious Self Transfer"
        return None 
class User: 
    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash

def require_auth():
    token = request.headers.get("Authorization")
    if token is None:
        return None, (jsonify({"error": "Not authorized"}), 401)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["username"], None
    except: 
        return None, (jsonify({"error": "Invalid token"}), 401)

@app.route("/accounts/<id>", methods=["GET"])
def get_account(id):
    username, error = require_auth()
    if error: 
        return error
    account = store.find_account(id)
    if account is None:
        return jsonify({"error": "Account not found"}), 404
    return jsonify ({"id": account.id, "owner_name": account.owner_name, "balance_cents" : account.balance_cents, "available_balance": account.available_balance()})

@app.route("/transfers", methods=["POST"])
def create_transfer():
    username, error = require_auth()
    if error: 
        return error
    data = request.json
    transfer = engine.initiate_transfer(data["idempotency_key"], data["sender_id"], data["receiver_id"], data["amount_cents"])
    if transfer.state == TransactionState.INITIATED:
        engine.process_transfer(transfer)
    return jsonify({"id": transfer.id, "transfer_state": transfer.state.value, "amount_cents" : transfer.amount_cents, "fee_cents": transfer.fee_cents, "total_cents": transfer.total_cents, "failure_reason": transfer.failure_reason})

@app.route("/transfers/<id>", methods=["GET"])
def get_transfer(id):
    username, error = require_auth()
    if error: 
        return error
    transfer = store.find_transactions(id)
    if transfer is None:
        return jsonify({"error": "Account not found"}), 404
    return jsonify({"id": transfer.id, "transfer_state": transfer.state.value, "amount_cents" : transfer.amount_cents, "fee_cents": transfer.fee_cents, "total_cents": transfer.total_cents, "failure_reason": transfer.failure_reason})
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = data["password"]
    balance = data["balance_cents"]
    if store.find_user(username):
        return jsonify({"error": "Username already exists"}), 409
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")
    user = User(username, password_hash)
    account = Account(username, username, balance)
    store.save_user(user)
    store.save_account(account)
    token = jwt.encode({"username": username}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})


@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.json
    username = data["username"]
    password = data["password"]
    user = store.find_user(username)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({"error": "Wrong password"}), 401
    token = jwt.encode({"username": username}, SECRET_KEY, algorithm="HS256")
    return jsonify({"token": token})

store = Store()
ledger = Ledger(store)
engine = Engine(store, ledger)

if __name__ == "__main__":
    app.run(debug=True, port=5001)