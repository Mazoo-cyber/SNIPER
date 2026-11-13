#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نقطة الدخول السحابية الموحدة (GitHub Actions — v4.0 الخيار الأول):
- تستدعي مباشرةً الملف الموحد المطور (binance_scanner_standalone.py) دون الاعتماد على الملفات المقسمة القديمة.
- تحدد تلقائياً هل المطلوب فحص تأكيد 02:45 (--confirm-0245) أم المسح الشامل (--run-scan) بناءً على زر المستخدم أو توقيت الرياض.
- ترسل إشعار تيليجرام مدمج يعرض الصفقات المجازة ضمن بوابة المخاطرة الذكية إن كان مفعلاً.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

RIYADH = dt.timezone(dt.timedelta(hours=3))
BASE = os.path.dirname(os.path.abspath(__file__))

# خريطة cron المجدولة (بتوقيت UTC كما في scanner.yml) -> الوضع المقصود لكل موعد
CRON_MODE = {
    "45 23 * * *": "confirm",   # 02:45 الرياض — فحص تأكيدي
    "5 0 * * *": "scan",        # 03:05
    "5 8 * * *": "scan",        # 11:05
    "5 12 * * *": "scan",       # 15:05
    "5 16 * * *": "scan",       # 19:05
    "5 20 * * *": "scan",       # 23:05
}


def intended_run_info():
    """(mode, delay_minutes) من سياق الجدولة الفعلي github.event.schedule — لا من وقت التنفيذ.
    هذا يحل جوهر مشكلة تأخر Actions: طلب 02:45 الذي يصل 03:15 يظل تأكيداً لا مسحاً."""
    cron = (os.environ.get("SCHEDULE_CRON") or "").strip()
    if cron not in CRON_MODE:
        return None, None
    try:
        parts = cron.split()
        hh, mm = int(parts[1]), int(parts[0])
        now_utc = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
        intended = now_utc.replace(hour=hh, minute=mm)
        if intended > now_utc:
            intended -= dt.timedelta(days=1)
        delay = (now_utc - intended).total_seconds() / 60.0
        return CRON_MODE[cron], delay
    except Exception:
        return None, None


def _tp_hit(x):
    """أي صفقة لمست هدفاً (مفردات جديدة + قديمة): tp_hits أو نصوص الحالة."""
    th = x.get("tp_hits")
    if isinstance(th, list) and any(th):
        return True
    st = str(x.get("status") or "")
    return st.startswith(("وصل", "اكتملت")) or ("حقق هدف" in st)


def send_telegram_summary(delay_min=None, reset_done=False):
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return

    if reset_done:
        now_str = dt.datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        app_url = ""
        if "/" in repo:
            owner, rname = repo.split("/", 1)
            app_url = f"https://{owner}.github.io/{rname}/"
        lines = [
            f"🗑️ *ريست شامل — {now_str} (الرياض)*",
            "تم مسح كل الصفقات وحالة التتبع والسجل التراكمي والأرشيف.",
            "✅ النظام جاهز لتسجيل الصفقات الجديدة ابتداءً من المسح القادم.",
        ]
        if app_url:
            lines += ["", f"🔗 [التقرير الفارغ]({app_url})"]
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": "\n".join(lines),
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
        try:
            urllib.request.urlopen(req, timeout=15).read()
            print("Telegram reset notice sent.")
        except Exception as e:
            print("Telegram warn:", e)
        return

    try:
        trades = json.load(open(os.path.join(BASE, "scan_result.json"), encoding="utf-8"))
        held = json.load(open(os.path.join(BASE, "held.json"), encoding="utf-8"))
        exp = json.load(open(os.path.join(BASE, "explosion_candidates.json"), encoding="utf-8"))
        meta = json.load(open(os.path.join(BASE, "scan_meta.json"), encoding="utf-8"))
    except Exception:
        return

    now_str = dt.datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
    longs = sum(1 for t in trades if t.get("side") == "LONG")
    shorts = sum(1 for t in trades if t.get("side") == "SHORT")
    approved = [t for t in trades if t.get("risk_gate_allowed")]
    open_win = sum(1 for x in held if str(x.get("status", "")).startswith("مفتوحة") and x.get("open_state") == "رابحة")
    tps = sum(1 for x in held if _tp_hit(x))
    pr = meta.get("portfolio_risk") or {}

    top_lines = []
    for t in (approved or trades)[:4]:
        side_ar = "شراء" if t.get("side") == "LONG" else "بيع"
        notional = float(t.get("position_notional_usd") or 0)
        rcash = float(t.get("actual_risk_cash") or 0)
        flag = "✅" if t.get("risk_gate_allowed") else "👁️"
        top_lines.append(
            f"{flag} {t['name']} ({side_ar} {t['grade']}/{t['reach']} · {t['score']:.1f}) — حجم {notional:,.0f}$ · مخاطرة {rcash:.0f}$"
        )

    exp_names = [f"🔥 {e['name']} ({e['grade']})" for e in (exp.get("active") or [])[:4]]

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    app_url = ""
    if "/" in repo:
        owner, rname = repo.split("/", 1)
        app_url = f"https://{owner}.github.io/{rname}/"

    lines = [
        f"📊 *ماسح بايننس المطور v4.1 — {now_str} (الرياض)*",
        f"المؤهلة: *{len(trades)}* (شراء {longs} · بيع {shorts}) | المجاز للتنفيذ: *{len(approved)}*",
        f"المخاطرة المفتوحة: *{pr.get('open_risk_cash', 0):.0f}$ ({pr.get('open_risk_pct', 0):.2f}%)* | 🟢 رابحة {open_win} · 🎯 أهداف {tps}",
    ]
    if pr.get("session_label_ar"):
        lines.append(f"الجلسة: {pr['session_label_ar']}")
    if delay_min is not None and delay_min > 15:
        lines.append(f"⏱️ *تنفيذ خارج المواعيد المتفق عليها* — تأخر {delay_min:.0f} دقيقة عن الموعد المخطط (تأخر إقلاع GitHub Actions)")
    if meta.get("api_degraded"):
        lines.append(f"⚠️ *تدهور بيانات API* — تعذّر جلب شموع {meta.get('api_failed_symbols', 0)} عملة في هذا المسح؛ التقرير قد يكون ناقصاً")
    if top_lines:
        lines += ["", "*أقوى الفرص الآن:*", *top_lines]
    if exp_names:
        lines += ["", "*قابلة للانفجار:* " + " · ".join(exp_names)]
    if app_url:
        lines += ["", f"🔗 [افتح التقرير الكامل على الجوال]({app_url})"]

    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
    try:
        urllib.request.urlopen(req, timeout=15).read()
        print("Telegram notification sent.")
    except Exception as e:
        print("Telegram warn:", e)


def main():
    mode = (os.environ.get("SCAN_MODE") or "auto").strip().lower()
    now_r = dt.datetime.now(RIYADH)
    cron_mode, delay_min = intended_run_info()

    if mode == "reset":
        cli_flag = "--reset"
    elif mode == "confirm":
        cli_flag = "--confirm-0245"
    elif mode == "scan":
        cli_flag = "--run-scan"
    elif cron_mode is not None:
        # التشغيل المجدول: القرار من الموعد المخطط نفسه (SCHEDULE_CRON) لا من وقت التنفيذ —
        # حتى لو تأخر Actions 60+ دقيقة يظل طلب 02:45 تأكيداً ولا يتحول إلى مسح بالخطأ (الأولوية #1)
        cli_flag = "--confirm-0245" if cron_mode == "confirm" else "--run-scan"
    else:
        # يدوي/محلي بلا سياق جدولة: نافذة تأكيد احتياطية موسّعة (02:30 – 03:30 بالرياض).
        # على GitHub لا تُستدعى أبداً (SCHEDULE_CRON دائماً موجود)؛ وللتشغيل المحلي حدد SCAN_MODE=scan/confirm صراحةً
        if (now_r.hour == 2 and now_r.minute >= 30) or (now_r.hour == 3 and now_r.minute <= 30):
            cli_flag = "--confirm-0245"
        else:
            cli_flag = "--run-scan"

    standalone_path = os.path.join(BASE, "binance_scanner_standalone.py")
    delay_txt = f" | تأخر التنفيذ {delay_min:.0f} دقيقة عن الموعد المخطط" if (delay_min is not None and delay_min > 15) else ""
    print(f"[cloud_entry v4.1] Riyadh={now_r.strftime('%Y-%m-%d %H:%M:%S')} | mode={mode} (cron={os.environ.get('SCHEDULE_CRON') or '—'}) -> binance_scanner_standalone.py {cli_flag}{delay_txt}")
    subprocess.check_call([sys.executable, standalone_path, cli_flag])
    send_telegram_summary(delay_min=delay_min, reset_done=(mode == "reset"))


if __name__ == "__main__":
    main()
