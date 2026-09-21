"""Retry an explicitly chosen capture batch without browser login or screenshots."""
from pathlib import Path
import argparse
import json
import logging
from excel_report import save_reports

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture_folder', help='Folder capture yang berisi summary.json')
    args = parser.parse_args()
    folder = Path(args.capture_folder).resolve()
    if not folder.is_dir():
        raise SystemExit('Folder capture tidak ditemukan.')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler(folder/'retry_excel.log',encoding='utf-8')])
    try:
        config_path = folder/'project_config.json'
        if not config_path.exists():
            config_path = ROOT/'config.json'
        cfg = json.loads(config_path.read_text(encoding='utf-8'))
        results = json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        good = [r for r in results if r.get('status') in {'graph_present','no_data'}]
        # Old summaries did not store project identity separately; check exact generated name.
        for r in good:
            if r.get('graph') != f"{cfg['project']}_{r['network']}_graph.png":
                raise ValueError('Nama gambar tidak cocok dengan project konfigurasi; hentikan retry.')
        result = save_reports(results,folder,cfg,ROOT)
        (folder/'excel_retry_result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        logging.info('Hasil retry: %s',result['status'])
        return 0
    except Exception:
        logging.exception('Retry gagal. Gambar tetap tersimpan; lihat retry_excel.log.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
