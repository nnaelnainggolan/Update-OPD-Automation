"""Stage 2: local capture only. Never writes Drive or changes network settings."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import csv
import io
import json
import logging
import re
import shutil
import subprocess
import tempfile
import time

from PIL import Image, ImageEnhance, ImageOps
from playwright.sync_api import sync_playwright
from screenshot_reader import analyze, detect_port_color, port_strip_box
from session_helper import restore_session, close_safely

ROOT = Path(__file__).resolve().parent
WIB = timezone(timedelta(hours=7))


def validate_range(text, today):
    match = re.search(r'(20\d{2}/\d{1,2}/\d{1,2})\s*[~–—-]\s*(20\d{2}/\d{1,2}/\d{1,2})\s*Speed Summary', text)
    if not match:
        raise ValueError('Tanggal Speed Summary tidak terbaca.')
    start, end = (datetime.strptime(v, '%Y/%m/%d').date() for v in match.groups())
    if (start, end) != (today - timedelta(days=1), today):
        raise ValueError(f'Rentang grafik {start} sampai {end} bukan kemarin sampai hari ini. Atur tanggal di Ruijie dan ulangi.')
    return end


def visible(locator):
    return [locator.nth(i) for i in range(locator.count()) if locator.nth(i).is_visible()]


def wait_visible_unique(locator, label, timeout=20000):
    # A hidden first match must not block other visible matches.
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        found = visible(locator)
        if len(found) == 1:
            return found[0]
        if len(found) > 1:
            raise RuntimeError(f'{label}: {len(found)} elemen terlihat; perlu selector lebih spesifik.')
        time.sleep(0.2)
    raise RuntimeError(f'{label}: tidak ada elemen terlihat setelah {timeout // 1000} detik.')


def click_unique(locator, label):
    wait_visible_unique(locator, label).click()


def profile_email(page):
    """Read the small profile header containing Switch Tenant, not its account list."""
    emails = set()
    for label in visible(page.get_by_text('Switch Tenant', exact=True)):
        value = label.evaluate(r"""el => {
            let node = el;
            for (let i = 0; node && i < 6; i++, node = node.parentElement) {
                const text = node.innerText || '';
                const matches = [...new Set(text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [])];
                if (matches.length > 1) return null;
                if (matches.length === 1 && text.length < 350) return matches[0];
            }
            return null;
        }""")
        if value:
            emails.add(value.lower())
    return next(iter(emails)) if len(emails) == 1 else None


def open_profile(page):
    """Avatar position observed in the supplied 1440px diagnostic screenshot.

    This is a stage-2 visual fallback, bounded to the tested viewport.
    Continue only if the expected menu becomes visible.
    """
    if visible(page.get_by_text('Switch Tenant', exact=True)):
        return
    viewport = page.viewport_size
    if not viewport or viewport['width'] != 1440:
        raise RuntimeError('Pembuka profil uji memerlukan viewport 1440px. Jangan ubah viewport dahulu.')
    # Avatar center in diagnostic.png is (1380,25). Some menus open on hover.
    page.mouse.move(1380, 25)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if visible(page.get_by_text('Switch Tenant', exact=True)):
            logging.info('Menu profil terbuka melalui hover avatar')
            return
        page.wait_for_timeout(200)
    page.mouse.click(1380, 25)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if visible(page.get_by_text('Switch Tenant', exact=True)):
            logging.info('Menu profil terbuka melalui klik avatar')
            return
        page.wait_for_timeout(200)
    raise RuntimeError('Avatar telah dituju tetapi menu Switch Tenant belum terlihat. Lihat diagnostic.png.')


def ensure_tenant(page, target):
    if not profile_email(page):
        open_profile(page)
    deadline = time.monotonic() + 10
    current = None
    while time.monotonic() < deadline:
        current = profile_email(page)
        if current:
            break
        page.wait_for_timeout(250)
    if not current:
        raise RuntimeError('Email tenant aktif pada header profil belum terbaca. Lihat diagnostic.png.')
    logging.info('Tenant pada header profil: %s', current)
    if current == target.lower():
        return
    buttons = visible(page.get_by_role('button', name='Switch Tenant', exact=True))
    if len(buttons) == 1:
        buttons[0].click()
    else:
        labels = visible(page.get_by_text('Switch Tenant', exact=True))
        if len(labels) != 1:
            raise RuntimeError('Tombol Switch Tenant ambigu; lihat diagnostic.png.')
        labels[0].click()
    click_unique(page.get_by_text(target, exact=True), 'Tenant tujuan')
    page.wait_for_timeout(2000)
    # Switch may keep the profile menu open; do not toggle it closed blindly.
    if not visible(page.get_by_text('Switch Tenant', exact=True)):
        open_profile(page)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if profile_email(page) == target.lower():
            return
        page.wait_for_timeout(300)
    raise RuntimeError('Tenant tujuan belum terverifikasi pada header profil. Lihat diagnostic.png.')



def project_heading_visible(page, name):
    # Workspace heading, excluding the left selector and its floating tree.
    for item in visible(page.get_by_text(name, exact=True)):
        box = item.bounding_box()
        if box and box['x'] >= 210 and 50 <= box['y'] < 180:
            return True
    return False


def project_search(page, timeout=10000):
    """Filter the observed left popup before testing uniqueness (1440px viewport)."""
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        candidates = []
        for item in visible(page.get_by_placeholder('Search', exact=True)):
            box = item.bounding_box()
            if box and 0 <= box['x'] < 400 and 100 <= box['y'] < 400:
                candidates.append(item)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise RuntimeError('Popup project memiliki lebih dari satu pencarian; navigasi dihentikan.')
        page.wait_for_timeout(200)
    raise RuntimeError('Kotak Search di popup project kiri belum terlihat setelah 10 detik.')


def select_project(page, name):
    click_unique(page.get_by_text('Project', exact=True), 'Menu Project')
    page.wait_for_timeout(800)
    if not project_heading_visible(page, name):
        # Bounded visual fallback from diagnostic_navigation.png, 1440px viewport.
        # Hover opens the project selector; selection uses exact text.
        if not page.viewport_size or page.viewport_size['width'] != 1440:
            raise RuntimeError('Pemilih project memerlukan viewport 1440px.')
        page.mouse.move(100, 84)
        logging.info('Hover nama project; menunggu popup daftar project')
        search = project_search(page)
        search.fill(name)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            matches = []
            for item in visible(page.get_by_text(name, exact=True)):
                box = item.bounding_box()
                if box and box['x'] < 400 and box['y'] >= 140:
                    matches.append(item)
            if len(matches) > 1:
                raise RuntimeError(f'Pilihan project {name} ambigu; navigasi dihentikan.')
            if len(matches) == 1:
                matches[0].click()
                break
            page.wait_for_timeout(200)
        else:
            raise RuntimeError(f'Project {name} tidak ditemukan pada dropdown setelah pencarian.')
        page.keyboard.press('Escape')
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if project_heading_visible(page, name):
            logging.info('Project terverifikasi pada judul workspace: %s', name)
            return
        page.wait_for_timeout(200)
    raise RuntimeError(f'Judul workspace belum menunjukkan {name}; capture dibatalkan.')


def navigate(page, cfg, already_open=False, check_tenant=True):
    logging.info('Memeriksa dashboard pada browser yang sama' if already_open else 'Membuka Home dan memeriksa sesi login')
    if not already_open:
        page.goto(cfg['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(2500)
    if '/sso/' in page.url or page.get_by_role('textbox', name='Password', exact=True).is_visible():
        raise RuntimeError('Halaman masih meminta login. Gunakan 05_LOGIN_DAN_CAPTURE.bat untuk login dan capture dalam browser yang sama.')
    if check_tenant:
        ensure_tenant(page, cfg['tenant'])
        page.keyboard.press('Escape')
        logging.info('Tenant terverifikasi: %s', cfg['tenant'])
    else:
        logging.info('Melanjutkan dalam tenant batch: %s', cfg['tenant'])
    select_project(page, cfg['project'])
    click_unique(page.get_by_text('View Topology', exact=True), 'View Topology')
    if cfg.get('auto_discover'):
        from auto_discovery import choose_gateway
        cfg['device_serial'] = choose_gateway(page)
    else:
        page.locator('#node_' + cfg['device_serial'] + ' > .devices-box').click(timeout=20000)
    page.get_by_text('Egress Traffic Trend', exact=True).click(timeout=20000)
    page.get_by_text(re.compile(re.escape(cfg['device_serial']))).first.wait_for(state='visible', timeout=20000)
    if cfg.get('auto_discover'):
        from auto_discovery import resolve_ports
        resolve_ports(page, cfg, click_unique)
    logging.info('Gateway project pengujian terbuka')


def _ocr_tsv(image, executable):
    with tempfile.TemporaryDirectory() as temp:
        input_path = Path(temp) / 'ocr.png'
        image.save(input_path)
        result = subprocess.run([executable, str(input_path), 'stdout', '--psm', '11', 'tsv'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Tesseract gagal: ' + result.stderr[:200])
    # QUOTE_NONE wajib: TSV Tesseract tidak memakai tanda kutip. Tanpa ini, satu token noise berupa "
    # membuka 'sel berkutip' yang menelan puluhan baris berikutnya (termasuk legenda Uplink/Downlink).
    return list(csv.DictReader(io.StringIO(result.stdout), delimiter='\t', quoting=csv.QUOTE_NONE))


def crop_original(path, executable, today):
    with Image.open(path) as src:
        original = src.convert('RGB')
        gray = ImageOps.grayscale(original)
        # Pass 1: pipeline asli (baik untuk grafik dan legenda berwarna).
        prepared = ImageEnhance.Contrast(gray).enhance(2.2)
        prepared = prepared.resize((prepared.width * 2, prepared.height * 2))
        try:
            info = analyze(_ocr_tsv(prepared, executable), original.size)
        except ValueError as first_error:
            # Pass 2 (cadangan): teks "No Data" berwarna abu-abu muda hilang pada kontras 2.2.
            # Threshold keras mempertahankannya. Hanya dipakai bila pass 1 gagal menemukan batas grafik.
            if 'Batas grafik tidak terbaca' not in str(first_error):
                raise
            hard = gray.point(lambda v: 0 if v < 235 else 255)
            hard = hard.resize((hard.width * 2, hard.height * 2))
            info = analyze(_ocr_tsv(hard, executable), original.size)
            if not info['no_data']:
                raise first_error
            logging.info('Pass cadangan OCR: No Data terbaca pada Speed Summary')
        if info['date'] != today or info['start_date'] != today - timedelta(days=1):
            raise ValueError('Tanggal OCR berbeda dari tanggal target.')
        crop = path.with_name(path.stem.replace('_original', '_graph') + '.png')
        original.crop(info['box']).save(crop)
        return crop, info


def read_port_color(original, folder, project, link):
    """Baca warna port terpilih dari screenshot. Kuning = link 10M/100M (di bawah 100 Mbps).

    Kegagalan membaca warna tidak menghentikan capture; hasilnya None.
    """
    try:
        with Image.open(original) as src:
            image = src.convert('RGB')
            found = detect_port_color(image)
            if not found:
                logging.warning('%s / %s: sorotan port tidak ditemukan; warna port tidak dibaca.', project, link)
                return None
            state = {'color': found['color'], 'image': None}
            if found['color'] == 'yellow':
                strip = folder / f'{project}_{link}_port.png'
                image.crop(port_strip_box(found['box'], image.size)).save(strip)
                state['image'] = strip.name
                logging.warning('%s / %s: PORT KUNING (10M/100M, di bawah 100 Mbps).', project, link)
            return state
    except Exception as exc:
        logging.warning('%s / %s: warna port gagal dibaca (%s).', project, link, exc)
        return None


def capture_link(page, cfg, link, folder, executable, today):
    port = cfg['ports'][link]
    logging.info('Memilih %s: %s', link, port)
    # Bring ports back after the preceding network's graph was scrolled.
    page.mouse.move(1100, 700)
    page.mouse.wheel(0, -2200)
    page.wait_for_timeout(600)
    click_unique(page.get_by_text(port, exact=True), port)
    description = cfg.get('descriptions', {}).get(link) or ('Metro Iforte' if link == 'METRO' else 'Broadband Nusanet')
    page.get_by_text(description, exact=True).wait_for(state='visible', timeout=20000)
    # Chart headings may be drawn on canvas and absent from DOM inner_text.
    original = folder / f"{cfg['project']}_{link}_original.png"
    last_error = None
    port_state = None
    for attempt in range(6):
        page.wait_for_timeout(2500)
        page.screenshot(path=str(original), animations='disabled')
        if port_state is None:
            # Baca warna port selagi deretan port terlihat (sebelum panel di-scroll).
            port_state = read_port_color(original, folder, cfg['project'], link)
        try:
            crop, info = crop_original(original, executable, today)
            if info['links'] and info['links'] != {link}:
                raise ValueError('Description OCR tidak cocok dengan jaringan yang dipilih.')
            break
        except ValueError as exc:
            last_error = exc
            # Do not scroll or accept a report with the wrong date.
            if 'Tanggal OCR' in str(exc):
                raise
            if attempt == 5:
                raise RuntimeError(f'Grafik lengkap belum terbaca setelah scroll: {last_error}') from exc
            logging.info('%s: grafik belum lengkap; scroll panel ke bawah (%s/5)', link, attempt+1)
            page.mouse.move(1100, 700)
            page.mouse.wheel(0, 180)
    else:
        raise RuntimeError(f'Grafik tidak terbaca: {last_error}')
    return {'network': link, 'port': port, 'status': 'no_data' if info['no_data'] else 'graph_present',
            'original': original.name, 'graph': crop.name, 'date': today.isoformat(),
            'port_color': port_state['color'] if port_state else None,
            'port_image': port_state['image'] if port_state else None,
            'review_required': True}


def login_in_context(context, page, cfg):
    page.goto(cfg['url'], wait_until='domcontentloaded')
    print('MODE CAPTURE v2.10.1: LOGIN DAN CAPTURE DALAM SATU BROWSER')
    print('Klik Login dan selesaikan verifikasi secara manual sampai Home/dashboard muncul.')
    print('Jangan tutup browser dan jangan menjalankan 02/04 bersamaan.')
    input('Saat dashboard Home terbuka, tekan Enter di terminal ini untuk MULAI CAPTURE: ')
    candidates = [tab for tab in context.pages if not tab.is_closed()
                  and tab.url.startswith('https://cloud-as.ruijienetworks.com/macc5/')]
    if not candidates:
        raise RuntimeError('Dashboard tidak ditemukan. Biarkan browser terbuka sampai login selesai.')
    page = candidates[-1]
    page.get_by_text('Project', exact=True).first.wait_for(state='visible', timeout=20000)
    return page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', action='store_true', help='Login manual lalu capture di context yang sama')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    today = datetime.now(WIB).date()
    folder = ROOT / 'captures' / datetime.now(WIB).strftime('%Y-%m-%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler(folder / 'run.log', encoding='utf-8')])
    executable = shutil.which(cfg['tesseract_command'])
    if not executable and Path(cfg['tesseract_command']).is_file():
        executable = cfg['tesseract_command']
    if not executable:
        logging.error('Tesseract tidak ditemukan. Periksa tesseract_command di config.json.'); return 1
    if not args.login and not (ROOT / 'browser-profile').exists():
        logging.error('Jalankan 02_LOGIN.bat terlebih dahulu.'); return 1
    results = []
    context = None
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(str(ROOT / 'browser-profile'),
                headless=False, viewport={'width':1440,'height':1100}, timezone_id='Asia/Jakarta')
            if not args.login:
                restore_session(context, ROOT / 'auth' / 'session.json')
            page = context.pages[0] if context.pages else context.new_page()
            if args.login:
                page = login_in_context(context, page, cfg)
            navigate(page, cfg, already_open=args.login)
            for link in ('METRO', 'BROADBAND'):
                try:
                    result = capture_link(page, cfg, link, folder, executable, today)
                    results.append(result)
                    logging.info('Tersimpan untuk diperiksa: %s', result['graph'])
                except Exception as exc:
                    results.append({'network':link, 'status':'failed', 'error':str(exc)})
                    logging.error('%s gagal: %s', link, exc)
                    try:
                        page.screenshot(path=str(folder / f'diagnostic_{link}.png'))
                        (folder / f'diagnostic_{link}.txt').write_text(
                            page.locator('body').inner_text(), encoding='utf-8')
                        logging.info('Diagnostik jaringan tersimpan: diagnostic_%s.png dan .txt', link)
                    except Exception:
                        logging.warning('Tidak dapat menyimpan diagnostik jaringan %s', link)
            try:
                from excel_report import save_reports
                excel_result = save_reports(results, folder, cfg, ROOT)
                (folder / 'excel_result.json').write_text(
                    json.dumps(excel_result, indent=2, ensure_ascii=False), encoding='utf-8')
            except Exception as exc:
                logging.error('Penyimpanan Excel gagal: %s. Gambar tetap tersedia di captures.', exc)
                (folder / 'excel_result.json').write_text(
                    json.dumps({'status':'failed','error':str(exc)}, indent=2), encoding='utf-8')
                return 1
            return 0 if all(r['status'] != 'failed' for r in results) else 1
        except Exception as exc:
            logging.error('Navigasi berhenti: %s', exc)
            try:
                if context and context.pages:
                    diagnostic_page = context.pages[-1]
                    if not diagnostic_page.is_closed() and '/macc5/' in diagnostic_page.url:
                        diagnostic_page.screenshot(path=str(folder / 'diagnostic.png'))
                        logging.info('Screenshot pemeriksaan: %s', folder / 'diagnostic.png')
            except Exception:
                logging.warning('Screenshot diagnostik tidak dapat diambil.')
            results.append({'status':'failed', 'error':str(exc)})
            return 1
        finally:
            (folder / 'summary.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
            if context:
                close_safely(context)
            logging.info('Hasil pengujian: %s', folder)

if __name__ == '__main__':
    raise SystemExit(main())
