const puppeteer = require('puppeteer');
const url = process.argv[2];

(async function main() {
  try {
    if (!url) throw "URL needed as first argument";

    /* Running with no sandbox is strongly discouraged. We trust GitHub.com for this use case. */
    const browser = await puppeteer.launch({args: ['--no-sandbox']});
    const [page] = await browser.pages();

    await page.goto(url, { waitUntil: 'networkidle0' });
    const data = await page.evaluate(() => document.querySelector('*').outerHTML);

    console.log(data);

    await browser.close();
  } catch (err) {
    console.error(err);
  }
})();
