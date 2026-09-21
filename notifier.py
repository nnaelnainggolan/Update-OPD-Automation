"""Ringkasan akhir batch: project dengan No Data, port kuning (<100 Mbps), atau capture gagal.

Selalu menyimpan notifikasi_gangguan.txt/.json di folder hasil batch.
Bila notify_config.json aktif, ringkasan yang sama dikirim lewat email (SMTP).
Kegagalan notifikasi tidak pernah mengubah hasil batch.
"""
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
import html
import json
import logging
import os
import smtplib
import ssl

from excel_report import MONTHS

WIB = timezone(timedelta(hours=7))
CONFIG_NAME = 'notify_config.json'
KIND_LABEL = {'GAGAL': 'GAGAL', 'EXCEL_GAGAL': 'EXCEL GAGAL', 'NO_DATA': 'NO DATA', 'PORT_KUNING': 'PORT KUNING'}
KIND_COLOR = {'NO_DATA': '#b45309', 'PORT_KUNING': '#a16207', 'GAGAL': '#b91c1c', 'EXCEL_GAGAL': '#b91c1c'}
YELLOW_DETAIL = 'Port berwarna kuning (10M/100M): kecepatan link di bawah 100 Mbps, indikasi gangguan.'
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # batas total gambar dalam satu email (Gmail: 25 MB)


def _short(text, limit=300):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def collect_issues(outcomes, projects):
    """Kembalikan (daftar catatan, daftar project yang belum diproses)."""
    by_name = {p['project']: p for p in projects}
    issues = []
    for outcome in outcomes:
        name = outcome['project']
        cfg = by_name.get(name, {})
        ports, descriptions = cfg.get('ports', {}), cfg.get('descriptions', {})
        folder = Path(outcome['folder']) if outcome.get('folder') else None

        def existing(filename):
            if folder and filename and (folder / filename).is_file():
                return str(folder / filename)
            return None

        for capture in outcome.get('captures', []):
            status = capture.get('status')
            network = capture.get('network') or '-'
            base = {'project': name, 'network': network,
                    'port': ports.get(network, capture.get('port', '-')),
                    'description': descriptions.get(network, '')}
            graph = existing(capture.get('graph'))
            if status == 'failed':
                issues.append({**base, 'kind': 'GAGAL', 'images': [],
                               'detail': _short(capture.get('error', 'Penyebab tidak tercatat.'))})
                continue
            if status == 'no_data':
                issues.append({**base, 'kind': 'NO_DATA', 'detail': 'Grafik Speed Summary kosong (No Data).',
                               'images': [{'path': graph, 'label': 'No Data'}] if graph else []})
            if capture.get('port_color') == 'yellow':
                images = []
                port_image = existing(capture.get('port_image'))
                if port_image:
                    images.append({'path': port_image, 'label': 'warna port'})
                if status != 'no_data' and graph:
                    images.append({'path': graph, 'label': 'grafik'})
                issues.append({**base, 'kind': 'PORT_KUNING', 'detail': YELLOW_DETAIL, 'images': images})
        excel = outcome.get('excel') or {}
        if excel.get('status') == 'failed':
            issues.append({'project': name, 'network': '-', 'port': '-', 'description': '', 'images': [],
                           'kind': 'EXCEL_GAGAL', 'detail': _short(excel.get('error', 'Penyebab tidak tercatat.'))})
    processed = {o['project'] for o in outcomes}
    pending = [p['project'] for p in projects if p['project'] not in processed]
    return issues, pending


def _started_from_folder(run_dir):
    try:
        return datetime.strptime(Path(run_dir).name[len('multi_'):], '%Y-%m-%d_%H%M%S_%f')
    except ValueError:
        return None


def _target(item):
    return item['project'] if item['network'] == '-' else f"{item['project']} / {item['network']} ({item['port']})"


def build_message(issues, pending, total, processed, run_dir, target_date, started, finished):
    date_label = f'{target_date.day:02d} {MONTHS[target_date.month]} {target_date.year}'
    failed = [i for i in issues if i['kind'] in ('GAGAL', 'EXCEL_GAGAL')]
    no_data = [i for i in issues if i['kind'] == 'NO_DATA']
    yellow = [i for i in issues if i['kind'] == 'PORT_KUNING']
    parts = []
    if no_data:
        parts.append(f'{len(no_data)} No Data')
    if yellow:
        parts.append(f'{len(yellow)} port kuning')
    if failed:
        parts.append(f'{len(failed)} gagal')
    if pending:
        parts.append(f'{len(pending)} belum diproses')
    subject = f'[OPD Ruijie] {date_label}: ' + (', '.join(parts) if parts else 'semua project normal')

    span = f'{started:%H:%M} - {finished:%H:%M} WIB' if started else ''
    lines = [f'Laporan capture Ruijie - {date_label}',
             f'Batch: {span}  |  Project diproses: {processed} dari {total}', '']
    if failed:
        lines.append(f'GAGAL ({len(failed)})')
        lines += [f"- {_target(i)} [{KIND_LABEL[i['kind']]}]: {i['detail']}" for i in failed]
        lines.append('')
    if no_data:
        lines.append(f'NO DATA ({len(no_data)})')
        lines += [f"- {_target(i)}" + (f" - {i['description']}" if i['description'] else '') for i in no_data]
        lines.append('')
    if yellow:
        lines.append(f'PORT KUNING - link di bawah 100 Mbps ({len(yellow)})')
        lines += [f"- {_target(i)}" + (f" - {i['description']}" if i['description'] else '') for i in yellow]
        lines.append('')
    if any(i.get('images') for i in no_data + yellow):
        lines += ['Screenshot No Data dan port kuning tertanam pada badan email (tampilan HTML).', '']
    if pending:
        lines.append(f'BELUM DIPROSES ({len(pending)}) - batch berhenti sebelum project ini:')
        lines.extend(f'- {name}' for name in pending)
        lines.append('')
    if not (issues or pending):
        lines += ['Semua project memiliki grafik data dan tidak ada port kuning.', '']
    if no_data:
        lines += ['Catatan No Data: grafik Speed Summary kosong. Ini indikasi WAN terputus atau',
                  'tidak ada lalu lintas, belum gangguan terkonfirmasi. Periksa di Ruijie.', '']
    if yellow:
        lines += ['Catatan port kuning: menurut legenda Ruijie, kuning berarti link 10M/100M',
                  '(di bawah 100 Mbps). Ini indikasi gangguan atau link turun kecepatan.', '']
    lines.append(f'Folder hasil: {run_dir}')
    text = '\n'.join(lines)

    def cell(value, style=''):
        return f'<td style="border:1px solid #ddd;padding:6px 10px;{style}">{html.escape(str(value))}</td>'

    rows = ''
    for i in failed + no_data + yellow:
        rows += ('<tr>' + cell(i['project']) + cell(i['network']) + cell(i['port'])
                 + cell(KIND_LABEL[i['kind']], f"color:{KIND_COLOR[i['kind']]};font-weight:bold;white-space:nowrap")
                 + cell(i['detail']) + '</tr>')
    table = ''
    if rows:
        head = ''.join(f'<th style="border:1px solid #ddd;padding:6px 10px;background:#f3f4f6;text-align:left">{h}</th>'
                       for h in ('Project', 'Jaringan', 'Port', 'Status', 'Keterangan'))
        table = f'<table style="border-collapse:collapse;font-size:14px"><tr>{head}</tr>{rows}</table>'

    shots, embedded, skipped, budget, number = '', [], 0, MAX_IMAGE_BYTES, 0
    for item in no_data + yellow:
        for image in item.get('images', []):
            path = image['path']
            size = Path(path).stat().st_size
            if size > budget:
                skipped += 1
                continue
            budget -= size
            number += 1
            cid = f'shot{number}@opd.local'
            embedded.append((cid, path))
            caption = f"{_target(item)} - {image['label']}"
            shots += (f'<p style="margin:16px 0 4px"><b>{html.escape(_target(item))}</b> - {html.escape(image["label"])}</p>'
                      f'<img src="cid:{cid}" alt="{html.escape(caption)}" style="max-width:100%;border:1px solid #ddd">')
    if shots:
        shots = ('<h4 style="margin:20px 0 0">Screenshot</h4>'
                 '<p style="margin:2px 0;color:#555">Klik kanan pada gambar, lalu pilih Copy image.</p>' + shots)
        if skipped:
            shots += f'<p style="color:#b45309">{skipped} gambar tidak disertakan karena melebihi batas ukuran email.</p>'
    pending_html = ''
    if pending:
        items = ''.join(f'<li>{html.escape(n)}</li>' for n in pending)
        pending_html = f'<p><b>Belum diproses ({len(pending)})</b> - batch berhenti sebelum project ini:</p><ul>{items}</ul>'
    notes = ''
    if no_data:
        notes += ('<p style="color:#555"><b>No Data:</b> grafik Speed Summary kosong. Ini indikasi WAN terputus atau '
                  'tidak ada lalu lintas, belum gangguan terkonfirmasi. Periksa di Ruijie.</p>')
    if yellow:
        notes += ('<p style="color:#555"><b>Port kuning:</b> menurut legenda Ruijie, kuning berarti link 10M/100M '
                  '(di bawah 100 Mbps). Ini indikasi gangguan atau link turun kecepatan.</p>')
    ok = '<p>Semua project memiliki grafik data dan tidak ada port kuning.</p>' if not (issues or pending) else ''
    html_body = (f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px">'
                 f'<h3 style="margin:0 0 4px">Laporan capture Ruijie - {html.escape(date_label)}</h3>'
                 f'<p style="margin:0 0 12px;color:#555">Batch: {html.escape(span)} | Project diproses: {processed} dari {total}</p>'
                 f'{table}{shots}{pending_html}{ok}{notes}'
                 f'<p style="color:#777;font-size:12px">Folder hasil: {html.escape(str(run_dir))}</p></div>')
    return subject, text, html_body, embedded


def load_config(root):
    path = Path(root) / CONFIG_NAME
    if not path.is_file():
        return None
    cfg = json.loads(path.read_text(encoding='utf-8'))
    return cfg if cfg.get('enabled', False) else None


def send_email(cfg, subject, text, html_body, images=()):
    recipients = cfg.get('to')
    recipients = [recipients] if isinstance(recipients, str) else list(recipients or [])
    if not recipients:
        raise ValueError('Daftar penerima ("to") pada notify_config.json kosong.')
    username = cfg.get('username', '')
    password = (os.environ.get('OPD_SMTP_PASSWORD') or cfg.get('password', '')).replace(' ', '')
    host, port = cfg.get('smtp_host', 'smtp.gmail.com'), int(cfg.get('smtp_port', 587))
    security = cfg.get('security', 'ssl' if port == 465 else 'starttls')
    if security != 'none' and not (username and password):
        raise ValueError('Username dan password aplikasi email belum diisi pada notify_config.json.')

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = cfg.get('from') or username
    message['To'] = ', '.join(recipients)
    message.set_content(text)
    message.add_alternative(html_body, subtype='html')
    html_part = message.get_body(preferencelist=('html',))
    for cid, path in images:
        html_part.add_related(Path(path).read_bytes(), maintype='image', subtype='png',
                              cid=f'<{cid}>', filename=Path(path).name, disposition='inline')

    context = ssl.create_default_context()
    server = (smtplib.SMTP_SSL(host, port, timeout=30, context=context) if security == 'ssl'
              else smtplib.SMTP(host, port, timeout=30))
    with server:
        if security == 'starttls':
            server.starttls(context=context)
        if username and password:
            server.login(username, password)
        server.send_message(message, to_addrs=recipients)
    return recipients


def notify_batch(outcomes, projects, run_dir, root, target_date):
    issues, pending = collect_issues(outcomes, projects)
    run_dir = Path(run_dir)
    finished = datetime.now(WIB)
    subject, text, html_body, images = build_message(
        issues, pending, len(projects), len(outcomes), run_dir, target_date,
        _started_from_folder(run_dir), finished)
    (run_dir / 'notifikasi_gangguan.txt').write_text(subject + '\n\n' + text, encoding='utf-8')
    (run_dir / 'notifikasi_gangguan.json').write_text(
        json.dumps({'subject': subject, 'issues': issues, 'pending': pending}, indent=2, ensure_ascii=False),
        encoding='utf-8')
    logging.info('Ringkasan: %s (lihat notifikasi_gangguan.txt)', subject)

    try:
        cfg = load_config(root)
    except Exception as exc:
        logging.error('notify_config.json tidak dapat dibaca: %s', exc)
        return
    if not cfg:
        logging.info('Email notifikasi nonaktif (notify_config.json tidak ada atau enabled=false).')
        return
    if not (issues or pending) and not cfg.get('send_when_no_issue', False):
        logging.info('Tidak ada No Data, port kuning, atau gangguan; email tidak dikirim.')
        return
    try:
        sent_to = send_email(cfg, subject, text, html_body, images)
        logging.info('Email notifikasi terkirim ke: %s (%d screenshot)', ', '.join(sent_to), len(images))
    except Exception as exc:
        logging.error('Email notifikasi gagal dikirim (%s): %s. Ringkasan tetap tersimpan di folder hasil.',
                      type(exc).__name__, str(exc).rstrip('.'))
