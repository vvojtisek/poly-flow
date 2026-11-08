import { expect, test, type Page } from "@playwright/test";

// The story library on a phone: shelf, reading with help, the ungraded comprehension check, the
// local read mark and the filters. Runs after first-usable.spec.ts (same stack), whose admin
// account it signs in with; the stories are files shipped with the backend, not seeded data.
test.beforeEach(async ({ page }) => {
  const welcome = page.locator('[role="dialog"][aria-labelledby="welcome-title"]');
  await page.addLocatorHandler(welcome, async () => {
    await welcome.getByRole("button", { name: "Přeskočit" }).click();
    await expect(welcome).toHaveCount(0);
  });
});

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Uživatelské jméno").fill(process.env.E2E_USER ?? "mama");
  await page.getByLabel("Heslo nebo PIN").fill(process.env.E2E_SECRET ?? "rodic-heslo-1");
  await page.keyboard.press("Enter");
  await page.waitForURL((u) => u.pathname === "/");
}

test("story library: read a story with help, check understanding, find it again", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await signIn(page);
  await page.goto("/stories/library");
  await expect(page.getByRole("heading", { name: "Knihovna příběhů" })).toBeVisible();
  // Drafts are labelled as drafts; the phone folds the intro.
  await expect(page.getByText("Texty jsou zatím návrh")).toBeVisible();
  await expect(page.getByText("Co je knihovna?")).toBeVisible();
  await expect(page.getByRole("heading", { name: /^A1 · \d+ textů/ })).toBeVisible();

  // Search folds accents and umlauts: "kuhe" finds "Kühe".
  const search = page.getByLabel("Hledat příběh");
  await search.fill("kuhe");
  await expect(page.getByRole("button", { name: /^Číst: .*Kühen/ })).toHaveCount(1);
  await search.fill("");

  await page.getByRole("button", { name: "Číst: Der Regenschirm" }).click();
  await expect(page).toHaveURL(/story=a1-01-umbrella/);
  await expect(page.getByRole("heading", { name: "Der Regenschirm" })).toBeVisible();
  const lines = page.locator("article ol li");
  await expect(lines.first()).toBeInViewport();
  await expect(page.getByText("Texty jsou zatím návrh")).toBeVisible();

  // Help per line, then for the whole text.
  await page.getByRole("button", { name: "Překlad věty 1", exact: true }).click();
  await expect(lines.first().locator('span[lang="cs"]')).toBeVisible();
  await page.getByRole("button", { name: "Ukázat překlad", exact: true }).click();
  await expect(lines.locator('span[lang="cs"]')).toHaveCount(await lines.count());

  // Comprehension check: a wrong pick only says so, another pick is allowed.
  const sets = page.locator("article fieldset");
  const questions = await sets.count();
  expect(questions).toBeGreaterThan(0);
  for (let q = 0; q < questions; q++) {
    const options = sets.nth(q).locator("button[lang]");
    for (let i = 0; i < (await options.count()); i++) {
      if (await options.nth(i).isDisabled()) continue;
      const right = sets.nth(q).getByLabel("správně", { exact: true });
      const wrong = sets.nth(q).getByLabel("není to ono", { exact: true });
      const before = await wrong.count();
      await options.nth(i).click();
      // The server answers: either right, or one more option marked "not it" and still open.
      await expect.poll(async () => (await right.count()) > 0 || (await wrong.count()) > before).toBe(true);
      if (await right.count()) break;
    }
    await expect(sets.nth(q).getByLabel("správně", { exact: true })).toBeVisible();
  }

  // Finishing marks the story read on this device and returns to the shelf.
  await page.getByRole("button", { name: /^(Dočteno, zpět|Zpět) do knihovny$/ }).last().click();
  await expect(page).not.toHaveURL(/story=/);
  await expect(page.getByRole("button", { name: "Číst: Der Regenschirm" }).getByLabel("přečteno")).toBeVisible();
  await page.getByRole("checkbox", { name: "Jen nepřečtené" }).check();
  await expect(page.getByRole("button", { name: "Číst: Der Regenschirm" })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("checkbox", { name: "Jen nepřečtené" })).toBeChecked();
  await expect(page.getByRole("button", { name: "Číst: Der Wachhund" })).toBeVisible();

  // An unknown story link explains itself instead of failing silently.
  await page.goto("/stories/library?story=zz-no-such-story");
  await expect(page.getByText("Tento příběh tu není k dispozici.")).toBeVisible();
  expect(errors).toEqual([]);
});
