"""Portable export contracts; run python3 -m unittest discover -s tests."""

import base64
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'code'))
import exportSite as export
import checkSite as checker
import buildSite as builder


class Payload(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.inside = False
        self.data = ''
        self.scripts = 0
        self.feed(document)

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.scripts += 1
            self.inside = dict(attrs).get('id') == 'portable-data'

    def handle_endtag(self, tag):
        if tag == 'script':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.data += data


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repository'
        (self.root / 'docs').mkdir(parents=True)
        shutil.copyfile(REPO / 'docs/index.html', self.root / 'docs/index.html')
        self.cards = []
        for number, (name, kind, types) in enumerate([
            ('Pikachu', 'Pokémon', ['Lightning']), ('Pikachu', 'Pokémon', ['Lightning']),
            ('Mew', 'Pokémon', ['Psychic']), ('Ultra Ball', 'Item', []),
            ('Basic Fire Energy', 'Basic Energy', []), ('Unown A', 'Pokémon', ['Psychic']),
            ('Unown B', 'Pokémon', ['Psychic']), ('Unown C', 'Pokémon', ['Psychic']),
        ], 1):
            card = dict(name=name, card_type=kind, types_en=types, number=str(number),
                        set_name='ABC', date='2026-01-01', effect='Look at the top card.',
                        img=f'https://example.test/{number}.png',
                        card_key='pikachu' if number < 3 else ('unown' if number > 5 else None))
            path = self.root / f'data_en/series/ABC/{number}.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(card), encoding='utf-8')
            self.cards.append(path)
        self.output = self.root / 'dist/sample'

    def test_complete_records_links_and_zero_network_image_fallback(self):
        report = export.export_site(self.root, self.output, limit=0)
        self.assertEqual((report['cards'], report['local_images'], report['missing_images']), (8, 0, 8))
        payload = json.loads(Payload((self.output / 'index.html').read_text()).data)
        self.assertEqual(payload['images'], {})
        index = payload['files']['index/en.json']
        self.assertIn('effect', index['fields'])
        self.assertEqual(len(index['cards']), 8)
        self.assertIn('pikachu', payload['files']['index/links.json']['cards'])
        self.assertNotIn('unown', payload['files']['index/links.json']['cards'])
        self.assertEqual(report['files']['index.html'], export.digest(self.output / 'index.html'))

    def test_inline_json_survives_script_terminator_and_unicode(self):
        card = json.loads(self.cards[0].read_text())
        card['name'] = '</ScRiPt><script>window.injected=true</script>概率\u2028\u2029'
        self.cards[0].write_text(json.dumps(card))
        export.export_site(self.root, self.output, limit=0)
        parsed = Payload((self.output / 'index.html').read_text())
        self.assertEqual(parsed.scripts, 2)
        index = json.loads(parsed.data)['files']['index/en.json']
        self.assertIn(card['name'], [row[index['fields'].index('name')] for row in index['cards']])

    def test_real_local_picture_is_copied_with_nested_path_and_encoded_spaces(self):
        path = self.cards[0]
        card = json.loads(path.read_text())
        new = path.with_name('概率 card.json')
        path.rename(new)
        archive = Path(self.temp.name) / 'archive'
        picture = archive / 'en/series/ABC/概率 card.png'
        picture.parent.mkdir(parents=True)
        picture.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
        report = export.export_site(self.root, self.output, limit=0, archive=archive)
        payload = json.loads(Payload((self.output / 'index.html').read_text()).data)
        stored = 'data_en/series/ABC/概率 card.json'
        self.assertEqual(report['local_images'], 1)
        self.assertIn('%20', payload['images'][stored])
        self.assertIn('%E6', payload['images'][stored])
        self.assertEqual((self.output / 'images/en/series/ABC/概率 card.png').read_bytes(), picture.read_bytes())
        self.assertEqual(card['img'], json.loads(new.read_text())['img'])
        expected_picture = picture.read_bytes()
        shutil.rmtree(archive)
        shutil.rmtree(self.root / 'data_en')
        builder.build_site(self.root, self.output)
        self.assertEqual(checker.check_site(self.output)['local_images'], 1)
        self.assertEqual((self.output / 'images/en/series/ABC/概率 card.png').read_bytes(), expected_picture)

    def test_refresh_removes_stale_owned_files_but_protects_authored_edits(self):
        export.export_site(self.root, self.output, limit=0)
        export.export_site(self.root, self.output, limit=3)
        self.assertEqual(json.loads((self.output / export.REPORT).read_text())['cards'], 3)
        (self.output / 'index.html').write_text('an authored edit')
        with self.assertRaisesRegex(ValueError, 'edited'):
            export.export_site(self.root, self.output)
        self.assertEqual((self.output / 'index.html').read_text(), 'an authored edit')

    def test_unmanaged_destination_source_and_extra_file_are_protected(self):
        self.output.mkdir(parents=True)
        (self.output / 'note.md').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            export.export_site(self.root, self.output)
        with self.assertRaises(ValueError):
            export.export_site(self.root, self.root)
        with self.assertRaises(ValueError):
            export.export_site(self.root, self.root / 'docs')
        (self.output / 'note.md').unlink()
        export.export_site(self.root, self.output)
        (self.output / 'note.md').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            export.export_site(self.root, self.output)

    def test_bad_language_set_and_limit_fail_before_changing_output(self):
        for args in ({'languages': ['../en']}, {'sets': ['missing']}, {'limit': -1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                export.export_site(self.root, self.output, **args)
        self.assertFalse(self.output.exists())

    def test_repository_site_is_allowed_and_self_contained(self):
        site = self.root / 'site'
        export.export_site(self.root, site, limit=0)
        shutil.rmtree(self.root / 'data_en')
        self.assertEqual(checker.check_site(site)['cards'], 8)

    def alter_bundle(self, change):
        page = self.output / 'index.html'
        source = page.read_text()
        old = Payload(source).data
        bundle = json.loads(old)
        change(bundle)
        page.write_text(source.replace(old, export.script_json(bundle)))
        report = json.loads((self.output / export.REPORT).read_text())
        report['files']['index.html'] = export.digest(page)
        (self.output / export.REPORT).write_text(json.dumps(report))

    def test_checker_rejects_encoded_escape_and_remote_artwork_even_with_valid_hash(self):
        for source in ('https://example.test/a.png', '//example.test/a.png', '/absolute.png', '../outside.png', '%2e%2e/outside.png', 'images\\..\\outside.png'):
            with self.subTest(source=source):
                if self.output.exists():
                    shutil.rmtree(self.output)
                export.export_site(self.root, self.output, limit=0)
                def change(bundle):
                    index = bundle['files']['index/en.json']
                    stored = index['cards'][0][index['fields'].index('path')]
                    bundle['images'] = {stored: source}
                self.alter_bundle(change)
                with self.assertRaises(ValueError):
                    checker.check_site(self.output)

    def test_checker_rejects_modified_missing_extra_and_symlink_files(self):
        for mode in ('edited', 'missing', 'extra', 'symlink'):
            with self.subTest(mode=mode):
                if self.output.exists():
                    shutil.rmtree(self.output)
                export.export_site(self.root, self.output, limit=0)
                page = self.output / 'index.html'
                if mode == 'edited':
                    page.write_text(page.read_text() + '<!-- edited -->')
                elif mode == 'missing':
                    page.unlink()
                elif mode == 'extra':
                    (self.output / 'note.md').write_text('authored')
                else:
                    (self.output / 'link').symlink_to(self.cards[0])
                with self.assertRaises(ValueError):
                    checker.check_site(self.output)

    def test_checker_rejects_inconsistent_records_and_remote_runtime_resources(self):
        export.export_site(self.root, self.output, limit=0)
        self.alter_bundle(lambda bundle: bundle['files']['index/en.json']['cards'].pop())
        with self.assertRaisesRegex(ValueError, 'count'):
            checker.check_site(self.output)
        shutil.rmtree(self.output)
        export.export_site(self.root, self.output, limit=0)
        page = self.output / 'index.html'
        page.write_text(page.read_text().replace('</head>', '<script src="https://example.test/app.js"></script></head>'))
        report = json.loads((self.output / export.REPORT).read_text())
        report['files']['index.html'] = export.digest(page)
        (self.output / export.REPORT).write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'relative local file'):
            checker.check_site(self.output)

    @unittest.skipUnless(shutil.which('git'), 'Git is needed to check tracking rules')
    def test_site_artwork_is_tracked_while_full_archive_stays_ignored(self):
        folder = Path(self.temp.name) / 'ignore-check'
        folder.mkdir()
        shutil.copyfile(REPO / '.gitignore', folder / '.gitignore')
        subprocess.run(['git', 'init', '-q', str(folder)], check=True)
        result = subprocess.run(['git', '-C', str(folder), 'check-ignore', '--no-index', '--stdin'], input='site/index.html\nsite/images/en/card.jpg\nimages/en/card.jpg\n', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), ['images/en/card.jpg'])

    def test_ci_build_uses_current_viewer_without_source_data_or_archive(self):
        site = self.root / 'site'
        export.export_site(self.root, site, limit=0)
        before = checker.check_site(site)
        payload_before = Payload((site / 'index.html').read_text()).data
        shutil.rmtree(self.root / 'data_en')
        template = self.root / 'docs/index.html'
        template.write_text(template.read_text().replace('Pokémon Card Atlas', 'Latest viewer edit'))
        after = builder.build_site(self.root, site)
        self.assertIn('Latest viewer edit', (site / 'index.html').read_text())
        self.assertEqual(Payload((site / 'index.html').read_text()).data, payload_before)
        self.assertEqual(after['generated_at'], before['generated_at'])
        self.assertEqual(after['source_data_sha256'], before['source_data_sha256'])
        self.assertEqual(after['viewer_sha256'], export.digest(template))
        self.assertEqual(checker.check_site(site)['cards'], 8)

    def test_ci_build_rejects_unsafe_template_without_changing_previous_site(self):
        site = self.root / 'site'
        export.export_site(self.root, site, limit=0)
        before = {path.name: path.read_bytes() for path in site.iterdir() if path.is_file()}
        template = self.root / 'docs/index.html'
        template.write_text(template.read_text().replace('</head>', '<script src="https://example.test/remote.js"></script></head>'))
        with self.assertRaises(ValueError):
            builder.build_site(self.root, site)
        self.assertEqual({path.name: path.read_bytes() for path in site.iterdir() if path.is_file()}, before)

    def test_source_dates_sort_chronologically_instead_of_month_names(self):
        cards = [dict(path='data_en/a.json', name='Pikachu', date='Sep 30, 2025'),
                 dict(path='data_en/b.json', name='Pikachu', date='Jan 9, 2026')]
        self.assertEqual(export.choose_cards(cards, 1)[0]['date'], 'Jan 9, 2026')
        self.assertEqual(export.release_rank({'date': '2026-01-09'}), export.release_rank(cards[1]))

    def test_selection_is_deterministic_diverse_and_contains_print_pair(self):
        records, hashes = export.read_cards(self.root, ['en'])
        first = export.choose_cards(records['en'], 5)
        self.assertEqual(first, export.choose_cards(records['en'], 5))
        self.assertEqual(sum(card['name'] == 'Pikachu' for card in first), 2)
        self.assertEqual(len({card['card_type'] for card in first}), 3)
        expected = hashlib.sha256()
        for path in sorted(self.cards):
            expected.update(path.relative_to(self.root).as_posix().encode() + b'\0' + path.read_bytes() + b'\0')
        self.assertEqual(hashes['en'], expected.hexdigest())


if __name__ == '__main__':
    unittest.main()
