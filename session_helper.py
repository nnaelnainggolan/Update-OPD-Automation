"""Save sessionStorage for the verified Ruijie origin, never login fields."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import Error

ORIGIN = 'https://cloud-as.ruijienetworks.com'


def close_safely(context):
    try:
        context.close()
    except Error as exc:
        message = str(exc).lower()
        if 'closed' not in message:
            raise


def save_session(page, destination):
    if page.is_closed():
        raise RuntimeError('Browser sudah ditutup. Ulangi login dan tekan Enter saat dashboard masih terbuka.')
    parsed = urlsplit(page.url)
    if f'{parsed.scheme}://{parsed.netloc}' != ORIGIN or not parsed.path.startswith('/macc5/'):
        raise RuntimeError('Dashboard belum terbuka. Selesaikan login dahulu lalu ulangi.')
    page.get_by_text('Project', exact=True).first.wait_for(state='visible', timeout=15000)
    data = page.evaluate('() => Object.fromEntries(Object.entries(sessionStorage))')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps({'origin': ORIGIN, 'session': data}), encoding='utf-8')
    temporary.replace(destination)


def restore_session(context, source):
    source = Path(source)
    if not source.exists():
        return
    data = json.loads(source.read_text(encoding='utf-8'))
    if data.get('origin') != ORIGIN or not isinstance(data.get('session'), dict):
        raise RuntimeError('File sesi tidak valid. Jalankan 02_LOGIN.bat kembali.')
    payload = json.dumps(data)
    context.add_init_script(script='''(() => {
        const saved = ''' + payload + ''';
        if (location.origin === saved.origin) {
            for (const [key, value] of Object.entries(saved.session)) {
                if (sessionStorage.getItem(key) === null) sessionStorage.setItem(key, value);
            }
        }
    })();''')
