import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ToastProvider } from "../components/toast";
import fixtures from "../test/fixtures.json";
import { mockApi } from "../test/server";
import { LeadDetailPage } from "./LeadDetailPage";
import { QueuePage } from "./QueuePage";

function renderAt(path: string) {
  return render(
    <ToastProvider>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<QueuePage />} />
          <Route path="/leads/:leadId" element={<LeadDetailPage />} />
        </Routes>
      </MemoryRouter>
    </ToastProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("QueuePage", () => {
  it("shows stats and every lead from the API, with the hottest pending lead first", async () => {
    mockApi({ "GET /api/stats": () => fixtures.stats, "GET /api/leads": () => fixtures.leads });
    renderAt("/");
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(fixtures.leads.length);
    expect(rows[0]).toHaveTextContent(fixtures.leads[0].lead_id);
    expect(screen.getByText("Need review").parentElement).toHaveTextContent(String(fixtures.stats.pending));
  });

  it("sends band, search and status filters to the API", async () => {
    const calls = mockApi({ "GET /api/stats": () => fixtures.stats, "GET /api/leads": () => fixtures.leads });
    renderAt("/?band=HOT&status=pending_review");
    await screen.findByRole("table");
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/Search lead id/), "Lisboa");
    await waitFor(() => {
      const last = calls.filter((c) => c.key === "GET /api/leads").at(-1)!;
      expect(last.url.searchParams.get("q")).toBe("Lisboa");
      expect(last.url.searchParams.getAll("band")).toEqual(["HOT"]);
      expect(last.url.searchParams.get("status")).toBe("pending_review");
    });
  });

  it("offers to load demo leads when the desk is empty", async () => {
    const empty = { ...fixtures.stats, total: 0, pending: 0 };
    const calls = mockApi({
      "GET /api/stats": () => empty,
      "GET /api/leads": () => [],
      "POST /api/demo/load": () => ({ created: [] }),
    });
    renderAt("/");
    await userEvent.setup().click(await screen.findByRole("button", { name: /Load demo leads/ }));
    await waitFor(() => expect(calls.some((c) => c.key === "POST /api/demo/load")).toBe(true));
  });
});

describe("LeadDetailPage", () => {
  const leadId = fixtures.detail.packet.lead.lead_id;
  const packetId = fixtures.detail.packet.packet_id;

  it("explains the band and lists property matches", async () => {
    mockApi({ [`GET /api/leads/${leadId}`]: () => fixtures.detail });
    renderAt(`/leads/${leadId}`);
    expect(await screen.findByText("Clear buy intent in the message")).toBeInTheDocument();
    for (const m of fixtures.detail.packet.matches) {
      expect(screen.getByText(m.listing.title)).toBeInTheDocument();
    }
  });

  it("approves as the signed-in agent and shows the decided state", async () => {
    const calls = mockApi({
      [`GET /api/leads/${leadId}`]: () => fixtures.detail,
      [`POST /api/packets/${packetId}/approve`]: () => fixtures.approved,
    });
    localStorage.setItem("leadDesk.agentId", "agent_ana");
    renderAt(`/leads/${leadId}`);
    const user = userEvent.setup();
    const [approve] = await screen.findAllByRole("button", { name: /Approve & present listings/ });
    await user.click(approve);
    await waitFor(() => expect(calls.find((c) => c.key.endsWith("/approve"))?.body).toMatchObject({ agent_id: "agent_ana" }));
    expect(await screen.findByText(/nothing was sent to the customer/)).toBeInTheDocument();
    screen.getAllByRole("button", { name: /Approve/ }).forEach((b) => expect(b).toBeDisabled());
  });

  it("excludes a ticked listing and asks the API to re-match", async () => {
    const calls = mockApi({
      [`GET /api/leads/${leadId}`]: () => fixtures.detail,
      [`POST /api/packets/${packetId}/reject`]: () => fixtures.detail,
    });
    renderAt(`/leads/${leadId}`);
    const user = userEvent.setup();
    const [firstNotFit] = await screen.findAllByRole("checkbox", { name: /Not a fit/ });
    await user.click(firstNotFit);
    const [rematch] = screen.getAllByRole("button", { name: /Exclude 1 & re-match/ });
    await user.click(rematch);
    await waitFor(() =>
      expect(calls.find((c) => c.key.endsWith("/reject"))?.body).toMatchObject({
        listing_ids: [fixtures.detail.packet.matches[0].listing.listing_id],
      }),
    );
  });

  it("needs a second click to reject the whole packet", async () => {
    const calls = mockApi({
      [`GET /api/leads/${leadId}`]: () => fixtures.detail,
      [`POST /api/packets/${packetId}/reject`]: () => ({
        ...fixtures.detail,
        packet: { ...fixtures.detail.packet, status: "rejected" },
      }),
    });
    renderAt(`/leads/${leadId}`);
    const user = userEvent.setup();
    const [reject] = await screen.findAllByRole("button", { name: /Reject packet/ });
    await user.click(reject);
    expect(calls.some((c) => c.key.endsWith("/reject"))).toBe(false);
    await user.click(screen.getAllByRole("button", { name: /Confirm reject packet/ })[0]);
    await waitFor(() => expect(calls.find((c) => c.key.endsWith("/reject"))?.body).toMatchObject({ listing_ids: [] }));
  });

  it("shows a not-found state for unknown leads", async () => {
    mockApi({});
    renderAt("/leads/lead_0000");
    expect(await screen.findByText(/lead_0000 was not found/)).toBeInTheDocument();
  });
});
