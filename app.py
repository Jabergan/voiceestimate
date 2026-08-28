#!/usr/bin/env python3
"""
VoiceEstimate — Hackyard 2026
Voice to professional estimate in seconds. Built for contractors in the field.
Stack: Flask + faster-whisper + Qwen3 8B + ReportLab + SQLite
"""

from flask import Flask, request, jsonify, Response
import json, os, tempfile, datetime, re, sqlite3, subprocess, urllib.request, urllib.parse

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'estimates.db')

# ── Whisper ───────────────────────────────────────────────────────────────────
from faster_whisper import WhisperModel
WHISPER = WhisperModel('small', device='cuda', compute_type='float16')
print('Whisper ready.')

# ── DB ────────────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS estimates (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        estimate_num TEXT,
        contractor   TEXT,
        phone        TEXT,
        customer     TEXT,
        address      TEXT,
        items_json   TEXT,
        materials    REAL,
        total        REAL,
        created_at   TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ── Qwen3 system prompt ───────────────────────────────────────────────────────
QWEN_SYSTEM = (
    "You are a construction estimating assistant. Extract line items from a verbal job description.\n"
    "Return ONLY a valid JSON array, no explanation, no markdown, no think tags.\n"
    'Format: [{"name": "...", "qty": 0.0, "unit": "...", "unit_price": 0.0, "total": 0.0}]\n'
    "Use the unit prices provided (numbers only). Calculate total = qty * unit_price.\n"
    "UNIT RULES:\n"
    "- Hauling/disposal: LOADS not SF. qty=loads, unit=load.\n"
    "- framing=LF, siding/insulation/drywall/roofing=SF, windows/doors=each, concrete=LF, plumbing=SF, HVAC=SF, painting=SF, labor=hour\n"
    "- Plumbing and HVAC: use home SF as qty."
)

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with open(os.path.join(BASE_DIR, 'templates/index.html')) as f:
        return f.read()

@app.route('/transcribe', methods=['POST'])
def transcribe():
    audio = request.files.get('audio')
    if not audio:
        return jsonify({'error': 'No audio'}), 400
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        audio.save(tmp.name)
        tmp_path = tmp.name
    wav = tmp_path.replace('.webm', '.wav')
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-i', tmp_path, '-ar', '16000', '-ac', '1', wav],
            capture_output=True, check=True
        )
        segs, _ = WHISPER.transcribe(wav, language='en',
            initial_prompt='framing lumber OSB sheathing vinyl siding roofing windows doors insulation drywall concrete footings electrical plumbing HVAC painting hauling labor')
        transcript = ' '.join(s.text for s in segs).strip()
        if not transcript:
            return jsonify({'error': 'Could not transcribe — try again'}), 500
        return jsonify({'transcript': transcript})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        for f in [tmp_path, wav]:
            try:
                os.unlink(f)
            except:
                pass

@app.route('/parse', methods=['POST'])
def parse():
    data = request.json or {}
    transcript = data.get('transcript', '')
    prices     = data.get('prices', {})
    if not transcript:
        return jsonify({'error': 'No transcript'}), 400
    rate_lines = [f"{v['label']} ({v['unit']}): {v['price']}" for v in prices.values()]
    prompt = "/no_think\n" + QWEN_SYSTEM + "\n\nUnit prices:\n" + "\n".join(rate_lines) + "\n\nJob description: " + transcript + "\n\nReturn JSON array only."
    try:
        payload = json.dumps({
            'model': 'qwen3:14b', 'prompt': prompt, 'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 512}
        }).encode()
        req = urllib.request.Request(
            'http://localhost:11434/api/generate', data=payload,
            headers={'Content-Type': 'application/json'}, method='POST'
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read()).get('response', '').strip()
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        s, e = raw.find('['), raw.rfind(']')
        if s == -1 or e == -1:
            return jsonify({'error': 'Parse failed — rephrase and try again'}), 500
        items = json.loads(raw[s:e+1])
        normalized = []
        for item in items:
            qty = float(item.get('qty', item.get('quantity', 0)))
            up  = float(item.get('unit_price', item.get('price', 0)))
            normalized.append({
                'name':       item.get('name', item.get('description', '')),
                'qty':        qty,
                'unit':       item.get('unit', ''),
                'unit_price': up,
                'total':      float(item.get('total', qty * up))
            })
        return jsonify({'items': normalized})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save():
    d = request.json or {}
    items = d.get('items', [])
    total = sum(float(i.get('total', 0)) for i in items) + float(d.get('materials', 0))
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'INSERT INTO estimates (estimate_num,contractor,phone,customer,address,items_json,materials,total,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
        (d.get('estimate_num',''), d.get('contractor',''), d.get('phone',''),
         d.get('customer', d.get('customer_name','')), d.get('address', d.get('customer_address','')), json.dumps(items),
         float(d.get('materials', 0)), total,
         datetime.date.today().strftime('%b %d, %Y'))
    )
    conn.commit()
    row_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return jsonify({'ok': True, 'id': row_id})

@app.route('/estimates')
def estimates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM estimates ORDER BY id DESC').fetchall()
    conn.close()
    cards = ''
    for r in rows:
        try:
            items = json.loads(r['items_json'])
        except:
            items = []
        params = urllib.parse.urlencode({
            'items': r['items_json'], 'contractor': r['contractor'],
            'phone': r['phone'], 'customer': r['customer'],
            'address': r['address'], 'materials': r['materials'],
            'estimate_num': r['estimate_num'], 'date': r['created_at']
        })
        cards += (
            '<div class="card">'
            '<div class="card-top"><span class="est-num">' + r['estimate_num'] + '</span>'
            '<span class="est-date">' + r['created_at'] + '</span></div>'
            '<div class="card-customer">' + (r['customer'] or 'No name') + '</div>'
            '<div class="card-addr">' + (r['address'] or '') + '</div>'
            '<div class="card-total">$' + f"{r['total']:,.0f}" + '</div>'
            '<a class="card-btn" href="/pdf?' + params + '" target="_blank">Download PDF</a>'
            '</div>'
        )
    if not cards:
        cards = '<p style="color:#888;text-align:center;margin-top:60px">No estimates yet.</p>'
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Estimate History</title><style>'
        '*{margin:0;padding:0;box-sizing:border-box}'
        'body{background:#0a0a0a;color:#f0f0f0;font-family:-apple-system,sans-serif;min-height:100vh}'
        'header{padding:20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #2a2a2a}'
        '.back{background:#1c1c1c;border:1px solid #2a2a2a;color:#f0f0f0;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:14px}'
        '.back:hover{border-color:#f97316;color:#f97316}'
        'h1{font-size:18px;font-weight:700}'
        '.grid{padding:20px;display:flex;flex-direction:column;gap:12px;max-width:600px;margin:0 auto}'
        '.card{background:#141414;border:1px solid #2a2a2a;border-radius:12px;padding:16px}'
        '.card-top{display:flex;justify-content:space-between;margin-bottom:6px}'
        '.est-num{font-size:12px;color:#f97316;font-weight:700}'
        '.est-date{font-size:12px;color:#888}'
        '.card-customer{font-size:16px;font-weight:600;margin-bottom:2px}'
        '.card-addr{font-size:13px;color:#888;margin-bottom:10px}'
        '.card-total{font-size:22px;font-weight:800;color:#f97316;margin-bottom:12px}'
        '.card-btn{display:block;background:#f97316;color:#000;text-align:center;padding:10px;border-radius:8px;font-weight:700;font-size:14px;text-decoration:none}'
        '</style></head><body>'
        '<header><a class="back" href="/">Back</a><h1>Estimate History</h1><span></span></header>'
        '<div class="grid">' + cards + '</div></body></html>'
    )

@app.route('/pdf')
def pdf():
    from pdf_generator import generate_pdf
    try:
        items = json.loads(request.args.get('items', '[]'))
    except:
        items = []
    data = {
        'contractor':   request.args.get('contractor', ''),
        'phone':        request.args.get('phone', ''),
        'customer':     request.args.get('customer', request.args.get('customer_name', '')),
        'address':      request.args.get('address', request.args.get('customer_address', '')),
        'materials':    float(request.args.get('materials', 0) or 0),
        'estimate_num': request.args.get('estimate_num', 'EST-001'),
        'date':         request.args.get('date', datetime.date.today().strftime('%b %d, %Y')),
    }
    pdf_bytes = generate_pdf(items, data)
    return Response(pdf_bytes, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename="{data["estimate_num"]}.pdf"'})

@app.route('/email', methods=['POST'])
def send_email():
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders
    from pdf_generator import generate_pdf

    d = request.json or {}
    to = d.get('to', '')
    if not to:
        return jsonify({'error': 'No recipient'}), 400

    items    = d.get('items', [])
    pdf_data = {
        'contractor':   d.get('contractor', ''),
        'phone':        d.get('phone', ''),
        'customer':     d.get('customer', ''),
        'address':      d.get('address', ''),
        'materials':    float(d.get('materials', 0) or 0),
        'estimate_num': d.get('estimate_num', 'EST-001'),
        'date':         d.get('date', datetime.date.today().strftime('%b %d, %Y')),
    }
    pdf_bytes = generate_pdf(items, pdf_data)

    GMAIL_USER = 'jabergan21@gmail.com'
    GMAIL_PASS = 'jutybhvyisxhpena'

    msg = MIMEMultipart()
    msg['From']    = GMAIL_USER
    msg['To']      = to
    msg['Subject'] = f"Estimate {pdf_data['estimate_num']} from {pdf_data['contractor']}"
    msg.attach(MIMEText(
        f"Hi {pdf_data['customer']},\n\nPlease find your estimate attached.\n\nThanks,\n{pdf_data['contractor']}\n\nGenerated by VoiceEstimate",
        'plain'
    ))
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{pdf_data["estimate_num"]}.pdf"')
    msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.sendmail(GMAIL_USER, to, msg.as_string())
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/estimates/json')
def estimates_json():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM estimates ORDER BY id DESC').fetchall()
    conn.close()
    result = []
    for r in rows:
        try:
            items = json.loads(r['items_json'])
        except Exception:
            items = []
        result.append({
            'id':           r['id'],
            'estimate_num': r['estimate_num'],
            'contractor':   r['contractor'],
            'phone':        r['phone'],
            'customer':     r['customer'],
            'address':      r['address'],
            'items':        items,
            'materials':    r['materials'],
            'total':        r['total'],
            'date':         r['created_at'],
        })
    return jsonify({'estimates': result})

@app.route('/estimates/<int:est_id>')
def estimate_by_id(est_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute('SELECT * FROM estimates WHERE id=?', (est_id,)).fetchone()
    conn.close()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    try:
        items = json.loads(r['items_json'])
    except Exception:
        items = []
    return jsonify({
        'id':           r['id'],
        'estimate_num': r['estimate_num'],
        'contractor':   r['contractor'],
        'phone':        r['phone'],
        'customer':     r['customer'],
        'address':      r['address'],
        'items':        items,
        'materials':    r['materials'],
        'total':        r['total'],
        'date':         r['created_at'],
    })


@app.route('/estimates/<int:est_id>', methods=['DELETE'])
def delete_estimate(est_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM estimates WHERE id=?', (est_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import threading
    def keep_warm():
        import time
        time.sleep(60)
        while True:
            try:
                p = json.dumps({'model': 'qwen3:14b', 'prompt': 'hi', 'stream': False,
                                'keep_alive': -1, 'options': {'num_predict': 1}}).encode()
                r = urllib.request.Request('http://localhost:11434/api/generate', data=p,
                                           headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(r, timeout=30):
                    pass
            except:
                pass
            time.sleep(180)
    threading.Thread(target=keep_warm, daemon=True).start()
    app.run(host='0.0.0.0', port=5055, debug=False)
