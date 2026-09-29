"""Render the committed card edition with the current viewer; no archive needed.

This is the GitHub Pages build. It keeps the committed data edition and artwork
intact. Use exportSite.py separately to choose a new card/data edition.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from checkSite import Page, check_site
from exportSite import REPORT, digest, publish_directory, render_viewer, validate_destination

ROOT = Path(__file__).resolve().parent.parent


def build_site(root, site):
    root = root.resolve()
    site = validate_destination(root, site)
    report = check_site(site)
    source = (site / 'index.html').read_text(encoding='utf-8')
    bundle = json.loads(Page(source).payloads[0])
    rendered = render_viewer(root, bundle)
    stage = Path(tempfile.mkdtemp(prefix='.ptcg-build-', dir=site.parent))
    try:
        shutil.copytree(site, stage, dirs_exist_ok=True)
        (stage / 'index.html').write_text(rendered, encoding='utf-8')
        report['files']['index.html'] = digest(stage / 'index.html')
        report['viewer_sha256'] = digest(root / 'docs/index.html')
        # generated_at remains the data edition's date, not a fresh scrape claim.
        (stage / REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        check_site(stage)
        publish_directory(stage, site)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / 'site')
    args = parser.parse_args()
    site = args.site if args.site.is_absolute() else ROOT / args.site
    try:
        report = build_site(ROOT, site)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        parser.exit(1, f'Site build failed: {error}\n')
    print(f"Rendered {report['cards']} committed cards and {report['local_images']} local pictures with the current viewer in {site}")


if __name__ == '__main__':
    main()
