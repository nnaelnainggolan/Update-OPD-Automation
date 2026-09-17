"""Manual login, followed by explicit session save and graceful close."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from session_helper import save_session, close_safely

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(
                str(ROOT / 'browser-profile'), headless=False,
                viewport={'width':1440,'height':1000}, timezone_id='Asia/Jakarta')
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(config['url'], wait_until='domcontentloaded')
            print('PERBAIKAN SESI v2.1 - Login manual sampai dashboard muncul.')
            print('Jangan tutup browser dengan tombol X. Biarkan dashboard tetap terbuka.')
            input('Saat dashboard terbuka, tekan Enter DI TERMINAL ini untuk menyimpan sesi... ')
            pages = [tab for tab in context.pages if not tab.is_closed() and '/macc5/' in tab.url]
            if not pages:
                raise RuntimeError('Dashboard tidak ditemukan atau browser sudah ditutup. Ulangi 02_LOGIN.bat.')
            save_session(pages[-1], ROOT / 'auth' / 'session.json')
            print('SESI TERSIMPAN. Program akan menutup browser; sesudah itu jalankan 04_UJI_CAPTURE.bat.')
            return 0
        except Exception as exc:
            print('LOGIN BELUM TERSIMPAN:', exc)
            return 1
        finally:
            if context:
                close_safely(context)

if __name__ == '__main__':
    raise SystemExit(main())
