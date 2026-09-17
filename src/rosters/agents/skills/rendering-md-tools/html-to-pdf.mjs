#!/usr/bin/env node
/** Print a local HTML document to PDF without opening a browser window. */

import { chromium } from 'playwright';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function usage() {
  console.error('Usage: html-to-pdf.mjs <input.html> [output.pdf]');
}

const [, , inputArg, outputArg] = process.argv;
if (!inputArg) {
  usage();
  process.exit(2);
}

const input = path.resolve(inputArg);
const output = outputArg
  ? path.resolve(outputArg)
  : input.replace(/\.[^.]+$/, '') + '.pdf';

let browser;
try {
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
  } catch (chromeError) {
    try {
      browser = await chromium.launch({ headless: true });
    } catch {
      throw chromeError;
    }
  }

  const page = await browser.newPage();
  await page.goto(pathToFileURL(input).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: output,
    format: 'Letter',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: false,
  });
  console.log(output);
} finally {
  if (browser) await browser.close();
}
