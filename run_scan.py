#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""واجهة توافقية — دورة المسح الكاملة (03:05 · 11:05 · 15:05 · 19:05 · 23:05).

هذا الملف كان جزءاً من القاعدة المقسّمة القديمة (core/engine/track/lifecycle/gen_report) والتي حُذفت
لمنع تضارب كتابة ملفات الحالة (tracker_state.json بصيغ مختلفة). كل المنطق مدمج الآن في الملف الموحد:

    python3 binance_scanner_standalone.py --run-scan

يُحوَّل هذا الوجه تلقائياً إلى الملف الموحد للحفاظ على أوامر التشغيل القديمة في RULES.md.
"""
import os
import subprocess
import sys

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    print("[run_scan] التحويل إلى الملف الموحد: binance_scanner_standalone.py --run-scan")
    subprocess.check_call([sys.executable, os.path.join(base, "binance_scanner_standalone.py"), "--run-scan"])
