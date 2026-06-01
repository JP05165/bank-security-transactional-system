#!/bin/bash

DATE=$(date +%Y-%m-%d)

mkdir -p logs

if [ -f audit_log.txt ]; then
    mv audit_log.txt logs/audit_log_$DATE.txt
else 
    echo "No audit_log.txt found to rotate"
fi

find logs/ -name "*.txt" -mtime +7 -delete

echo "Log rotation complete - archived to logs/audit_log_$DATE.txt"
