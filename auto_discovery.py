"""Read-only device/port discovery; ambiguity stops the current project."""
import logging
import re
import time


def gateway_serials_from_text(text):
    """Read adjacent serial/model lines, as present in diagnostic_navigation.txt."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    serials = set()
    for previous, model in zip(lines, lines[1:]):
        if re.fullmatch(r'(?:RG-)?EG\d+[A-Z0-9-]*', model, re.I):
            # Require a serial-shaped label, not a friendly device name.
            if re.fullmatch(r'[A-Z0-9]{10,24}', previous) and re.search(r'\d', previous):
                serials.add(previous)
    return sorted(serials)


def choose_gateway(page):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        serials = gateway_serials_from_text(page.locator('body').inner_text())
        if len(serials) > 1:
            raise RuntimeError('Lebih dari satu pasangan SN/model gateway EG ditemukan; perlu pemetaan SN.')
        if len(serials) == 1:
            serial = serials[0]
            # Use the exact device selector that already worked in configured mode.
            boxes = page.locator('#node_' + serial + ' > .devices-box')
            found = [boxes.nth(i) for i in range(boxes.count()) if boxes.nth(i).is_visible()]
            if len(found) > 1:
                raise RuntimeError('Elemen gateway dengan SN yang sama ambigu.')
            if len(found) == 1:
                found[0].click(timeout=10000)
                logging.info('Gateway ditemukan dari pasangan SN/model pada topologi: %s', serial)
                return serial
        page.wait_for_timeout(300)
    raise RuntimeError('Pasangan SN/model EG dan elemen gateway belum cocok; lihat diagnostik navigasi.')


def marked_ports(page):
    # Port label class observed in the user's runtime. Never read page-wide P/S.
    return page.locator('.txt-item__port').evaluate_all(r'''labels => {
      const visible = e => !!(e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
      return labels.filter(visible).map(label => {
        let node = label.parentElement;
        for (let n=0; node && n<4; n++, node=node.parentElement) {
          if (node.querySelectorAll('.txt-item__port').length !== 1) break;
          const text = (node.innerText || '').trim();
          const marks = [...new Set(text.split(/\s+/).filter(t => t === 'P' || t === 'S'))];
          if (marks.length === 1) return {port:label.innerText.trim(), mark:marks[0]};
        }
        return {port:label.innerText.trim(), mark:null};
      });
    }''')


def resolve_ports(page, cfg, click_unique):
    page.mouse.move(1100,700)
    page.mouse.wheel(0,-2200)
    deadline = time.monotonic()+15
    rows=[]
    while time.monotonic()<deadline:
        rows=marked_ports(page)
        if any(r['mark']=='P' for r in rows) and any(r['mark']=='S' for r in rows): break
        page.wait_for_timeout(300)
    resolved={}
    for network,mark in [('METRO','S'),('BROADBAND','P')]:
        candidates=sorted({r['port'] for r in rows if r['mark']==mark})
        matches=[]
        for port in candidates:
            click_unique(page.get_by_text(port,exact=True),port)
            # Require evidence that this exact port is selected before reading Description.
            wan = re.search(r'WAN\d+$', port)
            if not wan:
                continue
            try:
                page.get_by_text(re.compile(r'^Interface\s*:\s*' + re.escape(wan.group()) + r'$')).wait_for(state='visible',timeout=5000)
            except Exception:
                continue
            page.wait_for_timeout(800)
            expected=cfg['descriptions'][network]
            try:
                page.get_by_text(expected,exact=True).wait_for(state='visible',timeout=4000)
            except Exception:
                continue
            # Check twice to avoid accepting a transient description during update.
            page.wait_for_timeout(800)
            if page.get_by_text(expected,exact=True).is_visible(): matches.append(port)
        if len(matches)!=1:
            raise RuntimeError(f'{network}: ditemukan {len(matches)} port cocok tanda {mark} dan Description; perlu diperiksa. Kandidat: {candidates}')
        resolved[network]=matches[0]
    if resolved['METRO']==resolved['BROADBAND']: raise RuntimeError('Port kedua jaringan sama.')
    cfg['ports']=resolved
    logging.info('Port otomatis terverifikasi: %s',resolved)
