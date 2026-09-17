"""Record real Ruijie locators instead of guessing selectors from screenshots."""
from pathlib import Path
import json
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent

def main():
    if not (ROOT / 'browser-profile').exists():
        raise SystemExit('Jalankan 02_LOGIN.bat terlebih dahulu.')
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    folder = ROOT / 'recordings'
    folder.mkdir(exist_ok=True)
    output = folder / ('navigation_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.py')
    print('Rekam: profil > Switch Tenant > ' + config['tenant'])
    print('Lalu project ' + config['project'] + ' > gateway > Egress Traffic Trend.')
    print('Tampilkan Metro, lalu Broadband. Tunggu grafik dan tanggal muncul pada setiap pilihan.')
    print('Jika kembali ke login: tutup recorder; ulangi 02_LOGIN.bat. Jangan rekam password/OTP.')
    result = subprocess.run([
        sys.executable, '-m', 'playwright', 'codegen', '--target', 'python',
        '--user-data-dir', str(ROOT / 'browser-profile'),
        '--viewport-size', '1440,1000', '--timezone', 'Asia/Jakarta',
        '-o', str(output), config['url']], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    if output.exists():
        print('Rekaman tersimpan:', output)
        print('Periksa isinya sebelum dikirim. Jangan kirim browser-profile atau data sesi login.')
    else:
        print('Belum ada rekaman tersimpan. Ulangi 03_REKAM_NAVIGASI.bat.')

if __name__ == '__main__':
    main()
