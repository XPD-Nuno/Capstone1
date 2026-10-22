import { expect, test, type Page } from "@playwright/test";

function queueRow(page: Page, leadId: string) {
  return page.getByRole("row").filter({ has: page.getByRole("link", { name: leadId, exact: true }) });
}

test("queue → detail → exclude & re-match → approve", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Lead queue" })).toBeVisible();
  await expect(page.getByText("7 leads")).toBeVisible();

  await page.getByPlaceholder(/Search lead id/).fill("Lisboa");
  await expect(queueRow(page, "lead_9001")).toBeVisible();
  await page.getByRole("link", { name: "lead_9001", exact: true }).click();

  await expect(page).toHaveURL(/\/leads\/lead_9001$/);
  await expect(page.getByRole("heading", { name: "lead_9001" })).toBeVisible();
  await expect(page.getByText("Clear buy intent in the message")).toBeVisible();

  const notAFit = page.getByRole("checkbox", { name: /Not a fit/ });
  await expect(notAFit).toHaveCount(2);
  const excluded = (await page.getByText(/^mock_lst_\d+$/).first().textContent())!.trim();
  await notAFit.first().check();
  await page.getByRole("button", { name: "Exclude 1 & re-match" }).click();

  await expect(page.getByText(/Excluded 1 listing/)).toBeVisible();
  const matches = page.locator("section").filter({ has: page.getByRole("heading", { name: /Property matches/ }) });
  await expect(matches.getByRole("heading", { name: "Property matches (1)" })).toBeVisible();
  await expect(matches.getByRole("checkbox", { name: /Not a fit/ })).toHaveCount(1);
  // The only remaining mention is the "Excluded for this lead" note, not a listing card.
  await expect(matches.getByText(excluded, { exact: true })).toHaveCount(1);
  await expect(matches.getByText(/Excluded for this lead/)).toContainText(excluded);

  await page.getByRole("button", { name: /Approve/ }).click();
  await expect(page.getByText(/nothing was sent to the customer/)).toBeVisible();
  await expect(page.getByText(/Approved by agent_demo/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Approve/ })).toBeDisabled();
});

test("reject a whole packet with the two-step confirm", async ({ page }) => {
  await page.goto("/leads/lead_9002");
  await expect(page.getByRole("heading", { name: "lead_9002" })).toBeVisible();

  await page.getByRole("button", { name: "Reject packet" }).click();
  await page.getByRole("button", { name: "Confirm reject packet" }).click();

  await expect(page.getByText(/Packet rejected/)).toBeVisible();
  await expect(page.getByText(/Rejected by agent_demo/)).toBeVisible();

  await page.getByRole("link", { name: /Lead queue/ }).click();
  await expect(queueRow(page, "lead_9001")).toContainText("Approved");
  await expect(queueRow(page, "lead_9002")).toContainText("Rejected");
  await expect(page.getByRole("row").filter({ hasText: "Needs review" })).toHaveCount(5);
});
