#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""واجهة توافقية — إرسال ملخص تيليجرام لآخر مسح (تعتمد على cloud_entry.send_telegram_summary).

تعمل تلقائياً عند ضبط TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في البيئة.
"""
from cloud_entry import send_telegram_summary

if __name__ == "__main__":
    send_telegram_summary()
