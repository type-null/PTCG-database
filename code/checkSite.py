"""Check the committed Pages snapshot without reading any source data/archive."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
REPORT = 'export-report.json'


def local_file(site, reference):
    """Resolve a portable asset URL; never allow a host, root path or escape."""
    parts = urlsplit(reference)
    decoded = unquote(parts.path)
    if parts.scheme or parts.netloc or not decoded or decoded.startswith('/') or '\\' in decoded or '\x00' in decoded:
        raise ValueError(f'Asset must be a relative local file: {reference}')
    target = (site / decoded).resolve()
    if not target.is_relative_to(site) or not target.is_file():
        raise ValueError(f'Asset is missing or outside the site: {reference}')
    return target


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.payloads = []
        self.active = False
        self.assets = []
        self.styles = []
        self.style = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'script' and values.get('id') == 'portable-data':
            self.payloads.append('')
            self.active = True
        if values.get('src'):
            self.assets.append(values['src'])
        if tag == 'link' and set(values.get('rel', '').split()) & {'stylesheet', 'icon', 'preload', 'modulepreload'}:
            self.assets.append(values.get('href', ''))
        if tag == 'style':
            self.style = True

    def handle_data(self, value):
        if self.active:
            self.payloads[-1] += value
        if self.style:
            self.styles.append(value)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False
        if tag == 'style':
            self.style = False


def check_site(site):
    if site.is_symlink():
        raise ValueError('Site directory must not be a symlink')
    site = site.resolve()
    report = json.loads((site / REPORT).read_text(encoding='utf-8'))
    if report.get('schema') != 'ptcg-database-export-v1' or not isinstance(report.get('files'), dict):
        raise ValueError('Invalid export report')
    paths = list(site.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Pages artifacts must not contain symlinks')
    actual = {path.relative_to(site).as_posix() for path in paths if path.is_file()}
    if actual != set(report['files']) | {REPORT}:
        raise ValueError('Snapshot files differ from its export report')
    for name, expected in report['files'].items():
        path = local_file(site, name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Snapshot file changed since export: {name}')
    page = Page((site / 'index.html').read_text(encoding='utf-8'))
    if len(page.payloads) != 1:
        raise ValueError('Exactly one bundled-data payload is required')
    for asset in page.assets:
        local_file(site, asset)
    styles = '\n'.join(page.styles)
    if '@import' in styles.lower():
        raise ValueError('Keep the viewer CSS inline instead of importing a stylesheet')
    for match in re.finditer(r'url\(\s*[\'\"]?([^\'\")\s]+)', styles, flags=re.I):
        local_file(site, match.group(1))
    bundle = json.loads(page.payloads[0])
    summary = bundle['files']['index/summary.json']
    stored, count = set(), 0
    for language, details in summary.items():
        index = bundle['files'][f'index/{language}.json']
        position = index['fields'].index('path')
        if len(index['cards']) != details['cards']:
            raise ValueError(f'Card count differs for {language}')
        for row in index['cards']:
            if len(row) != len(index['fields']):
                raise ValueError(f'Invalid card row in {language}')
            stored.add(row[position])
        count += len(index['cards'])
    if not {'prints', 'cards'} <= bundle['files']['index/links.json'].keys():
        raise ValueError('Printing link tables are missing')
    if not set(bundle['images']) <= stored:
        raise ValueError('Artwork points to a card outside this selection')
    for asset in bundle['images'].values():
        local_file(site, asset)
    if report['cards'] != count or report['local_images'] != len(bundle['images']) or report['missing_images'] != count - len(bundle['images']):
        raise ValueError('Card or artwork coverage differs from the export report')
    if report['languages'] != summary:
        raise ValueError('Language metadata differs from the bundled records')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', nargs='?', type=Path, default=ROOT / 'site')
    args = parser.parse_args()
    try:
        report = check_site(args.site)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        parser.exit(1, f'Site check failed: {error}\n')
    print(f"Checked {report['cards']} cards and {report['local_images']} local pictures in {args.site.resolve()}")


if __name__ == '__main__':
    main()
