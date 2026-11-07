import { expect, test, type Page } from "@playwright/test";

// Desktop ergonomics: a whole lesson with the keyboard only. Runs after first-usable.spec.ts
// (same stack), whose admin account it signs in with.
const DE: Record<string, string> = { ich: "já", heißen: "jmenovat se", wie: "jak", du: "ty" };
const CS_TO_DE = Object.fromEntries(Object.entries(DE).map(([de, cs]) => [cs, de]));

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Uživatelské jméno").fill("mama");
  await page.getByLabel("Heslo nebo PIN").fill("rodic-heslo-1");
  await page.keyboard.press("Enter");
  await page.waitForURL((u) => u.pathname === "/");
}

test("a lesson runs on the keyboard: Enter, digit keys, Alt+S for ß", async ({ page }) => {
  await signIn(page);
  await page.goto("/lesson/vocabulary");
  await expect(page.getByRole("heading", { name: "Ahoj, jak se jmenuješ?" })).toBeVisible();
  // Enter: scene -> word cards -> practice
  await page.keyboard.press("Enter");
  for (let n = 1; n <= 4; n++) {
    await expect(page.getByText(`Slovo ${n} z 4`)).toBeVisible();
    await page.keyboard.press("Enter");
  }
  // The scene stays beside the practice on a wide screen.
  await expect(page.getByRole("heading", { name: "Úvodní scéna" })).toBeVisible();
  await expect(page.getByText("Klávesové zkratky").or(page.getByLabel("Klávesové zkratky"))).toBeVisible();

  for (let n = 1; n <= 8; n++) {
    await expect(page.getByText(`Úkol ${n} z 8`)).toBeVisible();
    const prompt = (await page.locator("section p.text-3xl").innerText()).trim();
    if (await page.getByText("Co znamená?").count()) {
      const texts = (await page.locator("[data-state]").allInnerTexts()).map((t) => t.replace(/^\d\s*/, "").trim());
      const index = texts.indexOf(DE[prompt]!);
      expect(index).toBeGreaterThanOrEqual(0);
      // Digit row by physical key: on a Czech layout the same key types "ě", "š", ...
      await page.keyboard.press(`Digit${index + 1}`);
      await expect(page.locator("p[aria-live=polite]")).toHaveText(`Správně! Správná odpověď: ${DE[prompt]}`);
      continue;
    }
    const word = CS_TO_DE[prompt]!;
    const box = page.getByLabel("Tvoje odpověď");
    await expect(box).toBeFocused();
    for (const ch of word) {
      if (ch === "ß") await page.keyboard.press("Alt+KeyS");
      else await page.keyboard.type(ch);
    }
    await expect(box).toHaveValue(word);
    await page.keyboard.press("Enter"); // submit
    await expect(page.getByText("Správně!")).toBeVisible();
    await page.keyboard.press("Enter"); // next
  }
  await expect(page.getByText("Lekce dokončena")).toBeVisible();
});

test("grammar lesson: notes beside the exercise, explanation after a mistake", async ({ page }) => {
  await signIn(page);
  await page.goto("/grammar");
  await expect(page.getByRole("heading", { name: "A1" })).toBeVisible();
  await page.getByRole("link", { name: /Já jsem, ty jsi: sloveso sein/ }).click();
  await expect(page.getByRole("heading", { name: "Já jsem, ty jsi: sloveso sein" })).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Cvičení 1 z 8")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Osobní zájmena a sein" })).toBeVisible(); // side pane
  // "Ich ___ müde.": options bin, bist, ist, sind. A wrong pick explains and lets the learner retry.
  await page.keyboard.press("Digit2");
  await expect(page.getByText("Proč:")).toBeVisible();
  await expect(page.getByText("Zkus to ještě jednou.")).toBeVisible();
  await page.keyboard.press("Digit1");
  await expect(page.getByText("Správně!")).toBeVisible();
  // "Proč?" (W): the curriculum explanation names the right sentence and the learner's mistake.
  await page.keyboard.press("KeyW");
  await expect(page.getByText("Správně: Ich bin müde.")).toBeVisible();
  await expect(page.getByText("Tvoje odpověď: bist")).toBeVisible();
  await expect(page.getByText("Vysvětlení z výkladu lekce")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Cvičení 2 z 8")).toBeVisible();
});
