"""Sequential configured projects; isolate each project's files, failures and Excel writes."""
from pathlib import Path
from datetime import datetime
import argparse
import json
import logging
import re
import shutil

from playwright.sync_api import sync_playwright
from capture_report import (ROOT, WIB, login_in_context, navigate, capture_link,
                            close_safely, restore_session, wait_visible_unique, ensure_tenant)
from excel_report import save_reports
from report_preflight import check_report


def load_projects(path):
    projects = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(projects, list):
        raise ValueError('projects.json harus berupa daftar project.')
    selected = []
    names, sheets, serials = set(), set(), set()
    for project in projects:
        if not project.get('enabled', True):
            continue
        for key in ('project','report_sheet') if project.get('auto_discover') else ('project','report_sheet','device_serial'):
            if not isinstance(project.get(key), str) or not project[key].strip():
                raise ValueError('Konfigurasi tidak lengkap: ' + key)
        name, sheet, serial = project['project'], project['report_sheet'].strip(), project.get('device_serial', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _-]*', name):
            raise ValueError('Nama project tidak aman untuk folder: ' + name)
        if not project.get('auto_discover') and not re.fullmatch(r'[A-Za-z0-9]+', serial):
            raise ValueError('Serial perangkat tidak valid.')
        if name in names or sheet in sheets or (serial and serial in serials):
            raise ValueError('Project, sheet, atau serial ganda dalam konfigurasi.')
        networks = project.get('networks', ['METRO','BROADBAND'])
        if not isinstance(networks, list) or not networks or len(set(networks)) != len(networks) or not set(networks) <= {'METRO','BROADBAND'}:
            raise ValueError('Daftar jaringan tidak valid: ' + name)
        if not project.get('auto_discover'):
            if set(project.get('ports', {})) != set(networks) or any(not isinstance(v, str) or not v.strip() for v in project['ports'].values()):
                raise ValueError('Port wajib tersedia untuk setiap jaringan aktif: ' + name)
            if len(set(project['ports'].values())) != len(networks):
                raise ValueError('Port jaringan tidak boleh sama.')
        expected_marks = {n: {'METRO':'S','BROADBAND':'P'}[n] for n in networks}
        if project.get('port_marks') != expected_marks:
            raise ValueError('Pemetaan tanda jaringan tidak sesuai kesepakatan.')
        if any(not project.get('descriptions', {}).get(n) for n in networks):
            raise ValueError('Description wajib tersedia untuk jaringan aktif.')
        names.add(name); sheets.add(sheet); serials.add(serial)
        selected.append(project)
    if not selected:
        raise ValueError('Tidak ada project aktif.')
    order_path = Path(path).parent / 'project_order.json'
    if order_path.exists():
        order = json.loads(order_path.read_text(encoding='utf-8'))
        if not isinstance(order, list) or any(not isinstance(n, str) for n in order):
            raise ValueError('project_order.json harus berisi daftar nama project.')
        if len(order) != len(set(order)):
            raise ValueError('Nama project ganda pada project_order.json.')
        rank = {name: i for i, name in enumerate(order)}
        unknown = [p['project'] for p in selected if p['project'] not in rank]
        if unknown:
            raise ValueError('Project belum tercantum dalam urutan Ruijie: ' + ', '.join(unknown))
        selected.sort(key=lambda p: rank[p['project']])
    return selected


def diagnostic(page, folder, label):
    try:
        if not page.is_closed() and '/macc5/' in page.url:
            page.screenshot(path=str(folder / f'diagnostic_{label}.png'))
            (folder / f'diagnostic_{label}.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
    except Exception:
        logging.warning('Diagnostik %s tidak dapat disimpan.', label)


def run_one(page, cfg, folder, executable, today, already_open, tenant_verified=False):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'project_config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    results = []
    excel = {'status':'not_attempted'}
    try:
        if already_open:
            # A client-side Home click retains the live login context.
            home = wait_visible_unique(page.get_by_text('Home', exact=True), 'Menu Home')
            home.click()
            page.wait_for_timeout(1500)
        navigate(page, cfg, already_open=already_open, check_tenant=not tenant_verified)
        (folder / 'project_config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        for link in cfg.get('networks', ['METRO','BROADBAND']):
            try:
                result = capture_link(page, cfg, link, folder, executable, today)
                result.update(project=cfg['project'], report_sheet=cfg['report_sheet'],
                              device_serial=cfg['device_serial'])
                results.append(result)
                logging.info('%s / %s: gambar tersimpan', cfg['project'], link)
            except Exception as exc:
                logging.error('%s / %s gagal: %s', cfg['project'], link, exc)
                results.append({'project':cfg['project'],'network':link,'status':'failed','error':str(exc)})
                diagnostic(page, folder, link)
        # Checkpoint images/metadata BEFORE any Drive operation for reliable retry.
        (folder / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        try:
            excel = save_reports(results, folder, cfg, ROOT)
        except Exception as exc:
            logging.exception('Excel %s gagal', cfg['project'])
            excel = {'status':'failed','error':str(exc)}
    except Exception as exc:
        logging.error('Navigasi %s gagal: %s', cfg['project'], exc)
        results.append({'project':cfg['project'],'status':'failed','error':str(exc)})
        diagnostic(page, folder, 'navigation')
    finally:
        (folder / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        (folder / 'excel_result.json').write_text(json.dumps(excel, indent=2), encoding='utf-8')
    failed = any(r['status']=='failed' for r in results) or excel['status']=='failed'
    return {'project':cfg['project'],'status':'failed' if failed else 'completed',
            'captures':results,'excel':excel,'folder':str(folder)}


def prepare_batch_tenant(page, cfg):
    """Called once, outside project failure handling: never skip failed tenant setup."""
    page.wait_for_timeout(1500)
    if '/sso/' in page.url or page.get_by_role('textbox', name='Password', exact=True).is_visible():
        raise RuntimeError('Login belum aktif. Selesaikan login sebelum memulai batch.')
    ensure_tenant(page, cfg['tenant'])
    page.keyboard.press('Escape')
    page.mouse.move(700, 100)
    logging.info('Tenant batch terverifikasi sekali: %s', cfg['tenant'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', action='store_true')
    parser.add_argument('--projects', default='projects.json')
    args = parser.parse_args()
    common = json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    projects = load_projects(ROOT/args.projects)
    run_dir = ROOT/'captures'/datetime.now(WIB).strftime('multi_%Y-%m-%d_%H%M%S_%f')
    run_dir.mkdir(parents=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(),logging.FileHandler(run_dir/'run.log',encoding='utf-8')])
    executable = shutil.which(common['tesseract_command'])
    if not executable and Path(common['tesseract_command']).is_file():
        executable = common['tesseract_command']
    if not executable:
        logging.error('Tesseract tidak ditemukan.'); return 1
    logging.info('v2.10.1: urutan project: %s', ', '.join(p['project'] for p in projects))
    raw_projects = json.loads((ROOT / args.projects).read_text(encoding='utf-8'))
    for pending in raw_projects:
        if not pending.get('enabled', True):
            logging.warning('Belum diaktifkan: %s — %s', pending.get('project'), pending.get('pending_reason', 'enabled=false'))
    today = datetime.now(WIB).date()
    try:
        preflight = check_report(projects, ROOT, today)
        (run_dir / 'preflight.json').write_text(json.dumps(preflight, indent=2), encoding='utf-8')
        logging.info('Pemeriksaan Excel sebelum batch: %s', preflight)
    except Exception as exc:
        logging.error('Batch belum dimulai: %s', exc)
        return 1
    outcomes = []
    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(str(ROOT/'browser-profile'),
                headless=False,viewport={'width':1440,'height':1100},timezone_id='Asia/Jakarta')
            if not args.login:
                restore_session(context, ROOT/'auth'/'session.json')
            page = context.pages[0] if context.pages else context.new_page()
            if args.login:
                page = login_in_context(context,page,common)
            if not args.login:
                page.goto(common['url'], wait_until='domcontentloaded')
            prepare_batch_tenant(page, common)
            today = datetime.now(WIB).date()
            for index, project in enumerate(projects):
                if page.is_closed():
                    logging.error('Browser ditutup. Sisa project tidak diproses.'); break
                cfg = {**common, **project}
                outcome = run_one(page,cfg,run_dir/project['project'],executable,today,
                                  already_open=True, tenant_verified=True)
                outcomes.append(outcome)
                (run_dir/'batch_summary.json').write_text(json.dumps(outcomes,indent=2),encoding='utf-8')
                if outcome['status'] != 'completed':
                    logging.error('Batch dihentikan: %s belum selesai. Project berikutnya tidak diproses. Periksa diagnostik lalu jalankan ulang.', project['project'])
                    break
            return 0 if len(outcomes)==len(projects) and all(o['status']=='completed' for o in outcomes) else 1
        except Exception:
            logging.exception('Proses batch berhenti.'); return 1
        finally:
            (run_dir/'batch_summary.json').write_text(json.dumps(outcomes,indent=2),encoding='utf-8')
            if context:
                close_safely(context)
            logging.info('Hasil batch: %s',run_dir)

if __name__=='__main__':
    raise SystemExit(main())
