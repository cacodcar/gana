// Exercise rendered controls against the installed theme, including mobile use.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: 'dark' });
    await page.goto('http://127.0.0.1:8765/index.html');
    const theme = () => page.locator('html').getAttribute('data-theme');
    const select = async mode => {
      await page.locator('.theme-switch-button').click();
      await page.locator(`.theme-change-button[data-mode="${mode}"]`).click();
    };
    assert.equal(await theme(), 'dark');
    assert.equal(await page.locator('.family-nav li').count(), 3);
    assert.equal(await page.locator('.family-current').count(), 1);
    assert.equal(await page.locator('.family-nav a').count(), 2);
    await select('light');
    assert.equal(await theme(), 'light');
    await page.reload();
    assert.equal(await theme(), 'light');
    await select('dark');
    assert.equal(await theme(), 'dark');
    await select('auto');
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'light');
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
    // Native keyboard activation must work for the appearance menu too.
    await page.locator('.theme-switch-button').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.theme-change-button[data-mode="auto"]').isVisible(), true);
    await page.keyboard.press('Escape');
    for (const width of [390, 768]) {
      await page.setViewportSize({ width, height: 844 });
      await page.locator('.primary-toggle').click();
      assert.equal(await page.locator('#pst-primary-sidebar-modal').evaluate(dialog => dialog.open), true);
      assert.equal(await page.locator('.family-nav').isVisible(), true);
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => !document.getElementById('pst-primary-sidebar-modal').open);
    }
    console.log('Passed: family navigation, theme modes/persistence/system changes, keyboard menu, mobile sidebar.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
