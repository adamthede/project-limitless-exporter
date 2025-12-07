#!/bin/bash
# Simple runner script for chat analysis

cd "$(dirname "$0")"
source venv/bin/activate
python analyze_chats.py --save-raw

