"""Optional browser regression checks of a generated, real-data export.

The committed site/ is ready to test; install Playwright and Chromium separately to run
these checks. The production app itself has no browser-tool dependency.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path(os.environ.get('PTCG_EXPORT_DIR', ROOT / 'site')).resolve()
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


@unittest.skipUnless(sync_playwright and (EXPORT / 'export-report.json').is_file(), 'Requires Playwright and a committed site/ snapshot')
class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch(executable_path=str(CHROME) if CHROME.is_file() else None, headless=True)
        cls.report = json.loads((EXPORT / 'export-report.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def open_page(self, root=EXPORT, width=390):
        context = self.browser.new_context(viewport={'width': width, 'height': 844})
        self.addCleanup(context.close)
        external, errors, missing, escaped = [], [], [], []
        context.route('http://**/*', lambda route: (external.append(route.request.url), route.abort()))
        context.route('https://**/*', lambda route: (external.append(route.request.url), route.abort()))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: missing.append(request.url))
        def inspect(request):
            parts = urlsplit(request.url)
            if parts.scheme == 'file' and not Path(unquote(parts.path)).resolve().is_relative_to(root.resolve()):
                escaped.append(request.url)
        page.on('request', inspect)
        page.goto((root / 'index.html').as_uri())
        page.wait_for_function('document.querySelectorAll(".card").length > 0')
        self.addCleanup(lambda: self.assertEqual((external, errors, missing, escaped), ([], [], [], [])))
        return page

    def test_search_filters_sort_details_and_printing_links_are_offline(self):
        page = self.open_page()
        page.locator('#q').fill('Pikachu')
        self.assertGreater(page.locator('.card').count(), 0)
        page.locator('.card').first.click()
        self.assertIn('Pikachu', page.locator('#detailBody h2').inner_text())
        self.assertGreater(page.locator('dd').count(), 5)
        self.assertGreater(page.locator('.ver').count(), 0)
        page.locator('.ver').first.click()
        self.assertIn('Pikachu', page.locator('#detailBody h2').inner_text())
        page.keyboard.press('Escape')
        self.assertFalse(page.locator('#detail').evaluate('(node) => node.open'))
        page.locator('#reset').click()
        page.locator('#type').select_option('Item')
        self.assertTrue(page.evaluate('filtered.length > 0 && filtered.every(card => card[idx("card_type")] === "Item")'))
        page.locator('#reset').click()
        page.locator('#order').select_option('new')
        self.assertTrue(page.evaluate('filtered.every((card, i) => i === 0 || releaseOrder(filtered[i - 1]) >= releaseOrder(card))'))
        page.locator('#q').fill('no such card 987654321')
        self.assertEqual(page.locator('.card').count(), 0)
        self.assertIn('No card matches', page.locator('#status').inner_text())

    def test_narrow_layout_and_detail_keep_controls_usable(self):
        for width in (1440, 390, 278):
            with self.subTest(width=width):
                page = self.open_page(width=width)
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                self.assertTrue(page.locator('.filters').evaluate('(node) => [...node.querySelectorAll("input,select,button")].every(item => item.getBoundingClientRect().height >= 44)'))
                page.locator('.card').first.click()
                self.assertFalse(page.locator('#detail').evaluate('(node) => node.scrollWidth > node.clientWidth'))
                page.locator('#detail').evaluate('(node) => node.scrollTop = node.scrollHeight')
                close = page.locator('.close').bounding_box()
                self.assertGreaterEqual(close['y'], 0)
                self.assertLess(close['y'] + close['height'], 844)
                page.locator('.close').click()
                page.emulate_media(reduced_motion='reduce')
                self.assertEqual(page.locator('.card').first.evaluate('(node) => getComputedStyle(node).transitionDuration'), '0s')

    def test_embedded_modal_sends_only_optional_focus_notification(self):
        with tempfile.TemporaryDirectory(prefix='ptcg host ') as temporary:
            host = Path(temporary) / 'index.html'
            host.write_text(f'''<!doctype html><html><body>
              <iframe src="{(EXPORT / 'index.html').as_uri()}" style="width:390px;height:900px"></iframe>
              <script>
                window.messages = [];
                addEventListener('message', event => {{
                  if (event.source === document.querySelector('iframe').contentWindow)
                    messages.push(event.data);
                }});
              </script></body></html>''')
            context = self.browser.new_context(viewport={'width': 800, 'height': 844})
            self.addCleanup(context.close)
            page = context.new_page()
            page.goto(host.as_uri())
            frame = page.frame_locator('iframe')
            frame.locator('#q').fill('Pikachu')
            frame.locator('.card').first.click()
            page.wait_for_function('messages.length === 1')
            self.assertEqual(page.evaluate('messages'), [{'type': 'type-null:focus-embed'}])
            frame.locator('.ver').first.click()
            self.assertEqual(page.evaluate('messages.length'), 1)

    def test_embed_handshake_replies_only_to_parent_ping(self):
        with tempfile.TemporaryDirectory(prefix='ptcg ping host ') as temporary:
            host = Path(temporary) / 'index.html'
            host.write_text(f'''<!doctype html><html><body>
              <iframe src="{(EXPORT / 'index.html').as_uri()}" style="width:390px;height:900px"></iframe>
              <script>
                window.messages = [];
                addEventListener('message', event => {{
                  if (event.source === document.querySelector('iframe').contentWindow)
                    messages.push(event.data);
                }});
              </script></body></html>''')
            context = self.browser.new_context(viewport={'width': 800, 'height': 844})
            self.addCleanup(context.close)
            page = context.new_page()
            page.goto(host.as_uri())
            frame = page.frame_locator('iframe')
            frame.locator('.card').first.wait_for()
            frame.locator('body').evaluate('''() => new Promise(resolve => {
              const observed = event => {
                if (event.source === window && event.data?.type === 'type-null:embed-ping') {
                  removeEventListener('message', observed);
                  parent.postMessage({type: 'test:barrier'}, '*');
                  resolve();
                }
              };
              addEventListener('message', observed);
              window.postMessage({type: 'type-null:embed-ping'}, '*');
            })''')
            page.wait_for_function("messages.some(message => message.type === 'test:barrier')")
            self.assertEqual(page.evaluate('messages'), [{'type': 'test:barrier'}])
            page.evaluate('''() => {
              messages = [];
              const frame = document.querySelector('iframe').contentWindow;
              frame.postMessage({type: 'unrelated-message'}, '*');
              frame.postMessage({type: 'type-null:embed-ping'}, '*');
            }''')
            page.wait_for_function('messages.length === 1')
            self.assertEqual(page.evaluate('messages'), [{'type': 'type-null:embed-ready'}])

    def test_moved_export_decodes_every_packaged_image(self):
        with tempfile.TemporaryDirectory(prefix='ptcg moved 概率 ') as temporary:
            copy = Path(temporary) / 'nested article/app'
            shutil.copytree(EXPORT, copy)
            page = self.open_page(copy)
            loaded = page.evaluate('''async () => {
              const sources = Object.values(bundle.images);
              return await Promise.all(sources.map(src => new Promise(resolve => {
                const image = new Image();
                image.onload = () => resolve(image.naturalWidth > 0);
                image.onerror = () => resolve(false);
                image.src = src;
              })));
            }''')
            self.assertEqual(len(loaded), self.report['local_images'])
            self.assertTrue(all(loaded))
            self.assertIn(f"{self.report['local_images']} local pictures", page.locator('#snapshot').inner_text())


if __name__ == '__main__':
    unittest.main()
