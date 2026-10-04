import { expect, test, type Page } from "@playwright/test";

// Plan §6 "první použitelná verze": profile creation -> lesson -> progress survives reload.
// The first German lesson takes the first four words of the "hallo" scene (data/scenes).
const DE: Record<string, string> = { ich: "já", heißen: "jmenovat se", wie: "jak", du: "ty" };
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
      await expect(page.getByText("Zkus to ještě jednou.")).toBeVisible(); // learning: the answer is shown
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

test("parent sets up, hands device to a child, lesson resumes after reload", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL("**/setup");
  await page.getByLabel("Jméno", { exact: true }).fill("Máma");
  await page.getByLabel("Uživatelské jméno").fill("mama");
  await page.getByLabel("Heslo", { exact: true }).fill(PARENT_PASSWORD);
  await page.getByRole("button", { name: "Vytvořit účet" }).click();
  await page.waitForURL("**/profiles");

  await page.getByLabel("Jméno", { exact: true }).fill("Eva");
  await page.getByLabel("Uživatelské jméno").fill("eva");
  await page.getByRole("button", { name: "Přidat profil" }).last().click();
  await expect(page.getByText("Profil vytvořen.")).toBeVisible();
  await page.getByRole("button", { name: "Předat zařízení" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  await expect(page.getByText("Teď se učí: Eva")).toBeVisible();
  await expect(page.getByRole("link", { name: "Rodina" })).toHaveCount(0);

  // Nothing has been learnt yet, so there is nothing to check.
  await expect(page.getByRole("button", { name: "Ověřit, co umím" })).toBeDisabled();
  await page.getByRole("button", { name: "Začít lekci" }).click();
  await page.waitForURL("**/lesson");

  // Context first: the scene, with Czech on demand, then the new words, then practice.
  await expect(page.getByRole("heading", { name: "Ahoj, jak se jmenuješ?" })).toBeVisible();
  await page.getByRole("button", { name: "Ukázat překlad" }).click();
  await expect(page.getByText("Ahoj, Anno! Já jsem Tom.")).toBeVisible();
  await page.getByRole("button", { name: "Seznámit se se slovy" }).click();
  for (let n = 1; n <= 4; n++) {
    await expect(page.getByText(`Slovo ${n} z 4`)).toBeVisible();
    await page.getByRole("button", { name: n === 4 ? "Procvičit" : "Další" }).click();
  }
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
    if (recall && firstRecall) firstRecall = false;
    await page.getByRole("button", { name: "Další" }).click();
  }
  await expect(page.getByText("Lekce dokončena")).toBeVisible();
  await expect(page.getByText("Tato slova si můžeš ověřit zítra v Ověření.")).toBeVisible();

  await page.getByRole("button", { name: "Na přehled" }).click();
  await page.waitForURL((u) => u.pathname === "/");
  const seen = page.getByText("Viděná slova").locator("xpath=preceding-sibling::p");
  await expect(seen).toHaveText("4");
  await page.reload();
  await expect(seen).toHaveText("4"); // progress is persisted server-side
  // Learnt today, checkable from tomorrow.
  await expect(page.getByRole("button", { name: "Ověřit, co umím" })).toBeDisabled();

  await page.getByRole("button", { name: "Zpět do rodičovského účtu" }).click();
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
  await expect(page.getByText("Neplatné jméno nebo heslo.")).toBeVisible(); // no PIN -> no solo login
});
