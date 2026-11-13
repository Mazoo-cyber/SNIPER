#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""واجهة توافقية — فحص التأكيد 02:45 (يُحوَّل إلى الملف الموحد).

المنطق الكامل (تأكيد قائمة 🔥 قابلة للانفجار + تحديث المراكز + بناء التقرير) مدمج في:

    python3 binance_scanner_standalone.py --confirm-0245

يُبقي هذا الوجه أمر `python3 confirm_0245.py` المذكور في RULES.md عاملاً بعد حذف القاعدة المقسّمة القديمة.
"""
import os
import subprocess
import sys

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    print("[confirm_0245] التحويل إلى الملف الموحد: binance_scanner_standalone.py --confirm-0245")
    subprocess.check_call([sys.executable, os.path.join(base, "binance_scanner_standalone.py"), "--confirm-0245"])
