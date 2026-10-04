import { expect, test, type Page } from "@playwright/test";

// Plan §6 "první použitelná verze": profile creation -> lesson -> progress survives reload.
const DE: Record<string, string> = { der: "ten (určitý člen)", und: "a", sein: "být", in: "v" };
const CS_TO_DE = Object.fromEntries(Object.entries(DE).map(([de, cs]) => [cs, de]));
const PARENT_PASSWORD = "rodic-heslo-1";

async function answerCorrectly(page: Page, opts: { wrongFirst?: boolean } = {}) {
  const prompt = (await page.locator("section p.text-3xl").innerText()).trim();
  if (await page.getByText("Co znamená?").count()) {
    const word = prompt.split(" ").at(-1)!;
    await page.getByRole("button", { name: DE[word]!, exact: true }).click();
  } else {
    const box = page.getByLabel("Tvoje odpověď");
    if (opts.wrongFirst) {
      await box.fill("falsch");
      await page.getByRole("button", { name: "Zkontrolovat" }).click();
      await expect(page.getByText("To není ono")).toBeVisible();
      await page.getByRole("button", { name: "Nápověda" }).click();
      await expect(page.getByText(/^\p{L}…$/u)).toBeVisible();
    }
    const expected = CS_TO_DE[prompt];
    expect(expected, `unexpected prompt ${prompt}`).toBeDefined();
    await box.fill(expected!);
    await page.getByRole("button", { name: "Zkontrolovat" }).click();
  }
  await expect(page.getByRole("button", { name: "Další" })).toBeVisible();
}

test("admin sets up, hands device to a child, lesson resumes after reload", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL("**/setup");
  await page.getByLabel("Jméno", { exact: true }).fill("Máma");
  await page.getByLabel("Uživatelské jméno").fill("mama");
  await page.getByLabel("Heslo", { exact: true }).fill(PARENT_PASSWORD);
  await page.getByRole("button", { name: "Vytvořit účet" }).click();
  await page.waitForURL("**/profiles");

  await page.getByLabel("Jméno", { exact: true }).fill("Eva");
  await page.getByLabel("Uživatelské jméno").fill("eva");
  await page.getByLabel("PIN (4–8 číslic)").fill("2468");
  await page.getByRole("button", { name: "Přidat profil" }).last().click();
  await expect(page.getByText("Profil vytvořen.")).toBeVisible();
  await page.getByRole("button", { name: "Předat zařízení" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  await expect(page.getByText("Teď se učí: Eva")).toBeVisible();
  await expect(page.getByRole("link", { name: "Rodina" })).toHaveCount(0);

  await page.getByRole("button", { name: "Začít lekci" }).click();
  await page.waitForURL("**/lesson");
  await expect(page.getByText("Úkol 1 z 8")).toBeVisible();
  await answerCorrectly(page);
  await page.getByRole("button", { name: "Další" }).click();
  await expect(page.getByText("Úkol 2 z 8")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Úkol 2 z 8")).toBeVisible();

  let firstRecall = true;
  for (let n = 2; n <= 8; n++) {
    await expect(page.getByText(`Úkol ${n} z 8`)).toBeVisible();
    const recall = (await page.getByText("Napiš slovo").count()) > 0;
    await answerCorrectly(page, { wrongFirst: recall && firstRecall });
    if (recall && firstRecall) {
      await expect(page.getByText(/nezapočítá/)).toBeVisible();
      firstRecall = false;
    }
    await page.getByRole("button", { name: "Další" }).click();
  }
  await expect(page.getByText("Lekce dokončena")).toBeVisible();
  await expect(page.getByText("7 / 8")).toBeVisible();

  await page.getByRole("button", { name: "Na přehled" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  const seen = page.getByText("Viděná slova").locator("xpath=preceding-sibling::p");
  await expect(seen).toHaveText("4");
  await page.reload();
  await expect(seen).toHaveText("4"); // progress is persisted server-side

  await page.getByRole("button", { name: "Zpět do účtu správce" }).click();
  await page.getByLabel("Heslo", { exact: true }).fill("spatne-heslo");
  await page.getByRole("button", { name: "Pokračovat" }).click();
  await expect(page.getByText("Neplatné jméno nebo heslo.")).toBeVisible();
  await page.getByLabel("Heslo", { exact: true }).fill(PARENT_PASSWORD);
  await page.getByRole("button", { name: "Pokračovat" }).click();
  await expect(page.getByRole("link", { name: "Rodina" })).toBeVisible();

  await page.getByRole("button", { name: "Odhlásit" }).click();
  await page.waitForURL("**/login");
  await page.getByLabel("Uživatelské jméno").fill("eva");
  await page.getByLabel("Heslo nebo PIN").fill("1234");
  await page.getByRole("button", { name: "Přihlásit se" }).click();
  await expect(page.getByText("Neplatné jméno nebo heslo.")).toBeVisible();
  await page.getByLabel("Heslo nebo PIN").fill("2468");
  await page.getByRole("button", { name: "Přihlásit se" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  await expect(page.getByText("Viděná slova").locator("xpath=preceding-sibling::p")).toHaveText("4"); // the child signs in alone
});
