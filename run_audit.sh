#!/bin/bash

source venv/bin/activate 

python3 bank_v2.py & 
PID=$!

sleep 3

if curl -s -X POST  http://127.0.0.1:5001/login > /dev/null; then
    echo "Flask is up"
else
   echo "Flask failed to start"
   kill $PID
   exit 1
fi

python3 security_test.py

kill $PID 
echo "Audit complete - Flask stopped"


