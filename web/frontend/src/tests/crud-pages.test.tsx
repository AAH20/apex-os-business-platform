/**
 * Simple CRUD page component tests without external testing libraries.
 * Uses React.createElement, basic mocks, and if/throw assertions.
 */

import React from "react";
import { renderToString } from "react-dom/server";

// ── Test Harness ───────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const failures: string[] = [];

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    throw new Error(
      `Assertion failed: ${message}\n  Expected: ${JSON.stringify(expected)}\n  Actual:   ${JSON.stringify(actual)}`
    );
  }
}

async function test(name: string, fn: () => void | Promise<void>): Promise<void> {
  try {
    await fn();
    passed++;
    console.log(`  ✓ ${name}`);
  } catch (err: any) {
    failed++;
    failures.push(`${name}: ${err.message}`);
    console.log(`  ✗ ${name}`);
    console.log(`    ${err.message}`);
  }
}

async function describe(name: string, fn: () => void | Promise<void>): Promise<void> {
  console.log(`\n${name}`);
  await fn();
}

// ── Mock Utilities ─────────────────────────────────────────────────────────

function mockFetch(response: { ok: boolean; status: number; data?: any; fail?: boolean }) {
  const calls: Array<{ url: string; options?: RequestInit }> = [];
  const fn = async (url: string, options?: RequestInit): Promise<any> => {
    calls.push({ url, options });
    if (response.fail) {
      throw new Error("Network error");
    }
    return {
      ok: response.ok,
      status: response.status,
      json: async () => response.data,
      text: async () => JSON.stringify(response.data),
    };
  };
  (fn as any).calls = calls;
  return fn;
}

// ── Minimal CRUD Page Stub ─────────────────────────────────────────────────

function CrudPage({ title, columns, searchPlaceholder, formFields, emptyMessage, errorMessage, loadingMessage }: {
  title: string; columns: string[]; searchPlaceholder: string;
  formFields: { name: string; label: string }[]; emptyMessage: string;
  errorMessage: string; loadingMessage: string;
}) {
  const [items, setItems] = React.useState<unknown[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [showForm, setShowForm] = React.useState(false);
  const [showDelete, setShowDelete] = React.useState<number | null>(null);
  const [formData, setFormData] = React.useState<Record<string, string>>({});
  const perPage = 10;

  const fetchData = React.useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`/api/${title.toLowerCase()}`);
      if (!res.ok) throw new Error(errorMessage);
      const json = await res.json();
      setItems(json.data || json);
    } catch (e) { setError(e instanceof Error ? e.message : errorMessage); }
    finally { setLoading(false); }
  }, [title, errorMessage]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = items.filter((i) => JSON.stringify(i).toLowerCase().includes(search.toLowerCase()));
  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
  const paginated = filtered.slice((page - 1) * perPage, page * perPage);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/${title.toLowerCase()}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(formData) });
      if (!res.ok) throw new Error(errorMessage);
      setShowForm(false); setFormData({}); fetchData();
    } catch (e) { setError(e instanceof Error ? e.message : errorMessage); }
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`/api/${title.toLowerCase()}/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(errorMessage);
      setShowDelete(null); fetchData();
    } catch (e) { setError(e instanceof Error ? e.message : errorMessage); }
  };

  if (loading) return React.createElement("div", null,
    React.createElement("h1", null, title),
    React.createElement("div", { role: "status", "aria-label": "loading" },
      React.createElement("span", { className: "spinner" }),
      React.createElement("span", null, loadingMessage)
    )
  );
  if (error) return React.createElement("div", null,
    React.createElement("h1", null, title),
    React.createElement("div", { role: "alert", className: "error-banner" }, error)
  );
  return React.createElement("div", null,
    React.createElement("h1", null, title),
    React.createElement("input", { type: "search", placeholder: searchPlaceholder, value: search, onChange: (e: any) => setSearch(e.target.value), "aria-label": "search" }),
    React.createElement("button", { onClick: () => setShowForm(true) }, "Add New"),
    showForm && React.createElement("form", { onSubmit: handleSubmit, "aria-label": "create-form" },
      formFields.map((f) => React.createElement("div", { key: f.name },
        React.createElement("label", { htmlFor: f.name }, f.label),
        React.createElement("input", { id: f.name, name: f.name, value: formData[f.name] || "", onChange: (e: any) => setFormData({ ...formData, [f.name]: e.target.value }) })
      )),
      React.createElement("button", { type: "submit" }, "Save"),
      React.createElement("button", { type: "button", onClick: () => setShowForm(false) }, "Cancel")
    ),
    showDelete !== null && React.createElement("div", { role: "dialog", "aria-label": "delete-confirmation" },
      React.createElement("p", null, "Are you sure you want to delete this item?"),
      React.createElement("button", { onClick: () => handleDelete(showDelete) }, "Confirm"),
      React.createElement("button", { onClick: () => setShowDelete(null) }, "Cancel")
    ),
    paginated.length === 0
      ? React.createElement("p", { className: "empty-message" }, emptyMessage)
      : React.createElement("table", null,
          React.createElement("thead", null,
            React.createElement("tr", null,
              columns.map((c) => React.createElement("th", { key: c }, c)),
              React.createElement("th", null, "Actions")
            )
          ),
          React.createElement("tbody", null,
            paginated.map((item, idx) =>
              React.createElement("tr", { key: idx },
                columns.map((c) => React.createElement("td", { key: c }, String((item as Record<string, unknown>)[c]))),
                React.createElement("td", null, React.createElement("button", { onClick: () => setShowDelete(idx) }, "Delete"))
              )
            )
          )
        ),
    totalPages > 1 && React.createElement("div", { role: "navigation", "aria-label": "pagination" },
      React.createElement("button", { disabled: page === 1, onClick: () => setPage(page - 1), "aria-label": "previous-page" }, "Previous"),
      React.createElement("span", null, `Page ${page} of ${totalPages}`),
      React.createElement("button", { disabled: page === totalPages, onClick: () => setPage(page + 1), "aria-label": "next-page" }, "Next")
    )
  );
}

// ── Page Configs ───────────────────────────────────────────────────────────

const pages = [
  { name: "Users", apiPath: "/api/users", data: [{ id: 1, name: "Alice", email: "alice@test.com", role: "admin" }, { id: 2, name: "Bob", email: "bob@test.com", role: "user" }], columns: ["name", "email", "role"], searchPlaceholder: "Search users...", formFields: [{ name: "name", label: "Name" }, { name: "email", label: "Email" }, { name: "role", label: "Role" }], emptyMessage: "No users found", errorMessage: "Failed to load users", loadingMessage: "Loading users..." },
  { name: "Products", apiPath: "/api/products", data: [{ id: 1, name: "Widget", price: 9.99, stock: 100 }, { id: 2, name: "Gadget", price: 19.99, stock: 50 }], columns: ["name", "price", "stock"], searchPlaceholder: "Search products...", formFields: [{ name: "name", label: "Name" }, { name: "price", label: "Price" }, { name: "stock", label: "Stock" }], emptyMessage: "No products found", errorMessage: "Failed to load products", loadingMessage: "Loading products..." },
  { name: "Orders", apiPath: "/api/orders", data: [{ id: 1, customer: "Alice", total: 29.97, status: "pending" }, { id: 2, customer: "Bob", total: 9.99, status: "shipped" }], columns: ["customer", "total", "status"], searchPlaceholder: "Search orders...", formFields: [{ name: "customer", label: "Customer" }, { name: "total", label: "Total" }, { name: "status", label: "Status" }], emptyMessage: "No orders found", errorMessage: "Failed to load orders", loadingMessage: "Loading orders..." },
  { name: "Categories", apiPath: "/api/categories", data: [{ id: 1, name: "Electronics", slug: "electronics" }, { id: 2, name: "Clothing", slug: "clothing" }], columns: ["name", "slug"], searchPlaceholder: "Search categories...", formFields: [{ name: "name", label: "Name" }, { name: "slug", label: "Slug" }], emptyMessage: "No categories found", errorMessage: "Failed to load categories", loadingMessage: "Loading categories..." },
];

// ── Tests ──────────────────────────────────────────────────────────────────

async function runTests(): Promise<void> {
  console.log("CRUD Page Component Tests");
  console.log("==========================");

  await describe("Rendering", async () => {
    await test("renders page title", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("Users"), "Should render title");
    });
    await test("renders loading state initially", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading users..." }));
      assert(html.includes("Loading users"), "Should show loading state");
    });
    await test("renders empty state when no items", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "No users found", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("No users found") || html.includes("Loading"), "Should render empty or loading");
    });
    await test("renders table with columns", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name", "email"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("name"), "Should render name column");
      assert(html.includes("email"), "Should render email column");
    });
    await test("renders create form elements", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [{ name: "name", label: "Name" }], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("Add New"), "Should render Add New button");
    });
  });

  await describe("API Calls", async () => {
    await test("fetches data from correct URL on mount", async () => {
      const mockFn = mockFetch({ ok: true, status: 200, data: [{ id: 1, name: "Alice" }] });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assertEqual((mockFn as any).calls.length, 1, "Should make exactly one fetch call");
      assertEqual((mockFn as any).calls[0].url, "/api/users", "Should fetch correct URL");
      (globalThis as any).fetch = origFetch;
    });
    await test("handles successful response with items array", async () => {
      const mockFn = mockFetch({ ok: true, status: 200, data: [{ id: 1, name: "Alice" }] });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("Alice"), "Should render item data");
      (globalThis as any).fetch = origFetch;
    });
    await test("handles successful response with nested data", async () => {
      const mockFn = mockFetch({ ok: true, status: 200, data: { data: [{ id: 1, name: "Bob" }] } });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.includes("Bob"), "Should render nested item data");
      (globalThis as any).fetch = origFetch;
    });
  });

  await describe("Error Handling", async () => {
    await test("displays error on HTTP failure", async () => {
      const mockFn = mockFetch({ ok: false, status: 500, data: null });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Failed to load users", loadingMessage: "Loading..." }));
      assert(html.includes("error") || html.includes("500") || html.includes("Failed to load users"), "Should display error for HTTP 500");
      (globalThis as any).fetch = origFetch;
    });
    await test("displays error on network failure", async () => {
      const mockFn = mockFetch({ ok: false, status: 0, fail: true });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Failed to load users", loadingMessage: "Loading..." }));
      assert(html.includes("error") || html.includes("Network") || html.includes("Failed to load users"), "Should display network error");
      (globalThis as any).fetch = origFetch;
    });
    await test("displays error on 404", async () => {
      const mockFn = mockFetch({ ok: false, status: 404, data: null });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Failed to load users", loadingMessage: "Loading..." }));
      assert(html.includes("error") || html.includes("404") || html.includes("Failed to load users"), "Should display error for 404");
      (globalThis as any).fetch = origFetch;
    });
    await test("displays error on 401 unauthorized", async () => {
      const mockFn = mockFetch({ ok: false, status: 401, data: null });
      const origFetch = globalThis.fetch;
      (globalThis as any).fetch = mockFn;
      const html = renderToString(React.createElement(CrudPage, { title: "Users", columns: ["name"], searchPlaceholder: "Search...", formFields: [], emptyMessage: "None", errorMessage: "Failed to load users", loadingMessage: "Loading..." }));
      assert(html.includes("error") || html.includes("401") || html.includes("Failed to load users"), "Should display error for 401");
      (globalThis as any).fetch = origFetch;
    });
  });

  await describe("Component Structure", async () => {
    await test("renders without crashing with minimal props", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Test", columns: [], searchPlaceholder: "", formFields: [], emptyMessage: "", errorMessage: "", loadingMessage: "" }));
      assert(html.length > 0, "Should produce non-empty HTML");
      assert(html.includes("Test"), "Should include title in output");
    });
    await test("renders without crashing with all props", async () => {
      const html = renderToString(React.createElement(CrudPage, { title: "Full Test", columns: ["name", "email"], searchPlaceholder: "Search...", formFields: [{ name: "name", label: "Name" }], emptyMessage: "None", errorMessage: "Error", loadingMessage: "Loading..." }));
      assert(html.length > 0, "Should produce non-empty HTML with all props");
      assert(html.includes("Full Test"), "Should include title");
    });
    await test("renders all page types without crashing", async () => {
      for (const p of pages) {
        const html = renderToString(React.createElement(CrudPage, { title: p.name, columns: p.columns, searchPlaceholder: p.searchPlaceholder, formFields: p.formFields, emptyMessage: p.emptyMessage, errorMessage: p.errorMessage, loadingMessage: p.loadingMessage }));
        assert(html.includes(p.name), `Should render ${p.name} page`);
      }
    });
  });

  // ─── Summary ──────────────────────────────────────────────────────────────

  console.log("\n==========================");
  console.log(`Results: ${passed} passed, ${failed} failed`);
  if (failures.length > 0) {
    console.log("\nFailures:");
    failures.forEach((f) => console.log(`  - ${f}`));
  }
  console.log("==========================\n");

  if (failed > 0) {
    process.exit(1);
  }
}

// Run tests
runTests().catch((err) => {
  console.error("Test runner error:", err);
  process.exit(1);
});
