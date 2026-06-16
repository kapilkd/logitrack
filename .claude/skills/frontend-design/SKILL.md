---
name: admin-ui-designer
description: Designs and generates modern, production-ready UI for admin-type projects — ERP, CRM, inventory, finance, logistics, operations dashboards — built on a React + TypeScript + Vite client with a single styles.css and inline SVG icons. Produces clean, fintech-leaning pages and components: stat cards, data tables, modals, slide-in panels, forms, badges, timelines, and conversion funnels. Use this skill whenever the user asks to design, build, create, redesign, improve, or style any page, screen, section, or component in an admin project — including phrasings like "design the X page", "create UI for X", "build a component for X", "make X look better", "redesign X", or any request about the frontend, layout, CSS, or visual polish of an admin application.
disable-model-invocation: true
---

# Admin UI Designer

You are designing frontend UI for **admin-type projects** — ERP systems, CRMs, inventory management, finance dashboards, procurement tools, operations portals, and similar. The goal is UI that feels like it belongs in a polished, modern business product — close in spirit to Linear, Notion, or modern banking dashboards — not generic Bootstrap-era output.

## Target stack

- **Client:** React 18 + TypeScript (strict mode), Vite, React Router 6
- **Styling:** single `styles.css` with CSS custom properties — no Tailwind, no CSS Modules, no styled-components
- **Icons:** inline SVG in `components/Icons.tsx` using `currentColor` — no icon CDN, no external icon library
- **State:** `useState` only — no Redux, Zustand, or Context
- **HTTP:** `api<T>()` wrapper around fetch — no raw `fetch()` in components
- **Filterable lists:** `useSearchParams`, not `useState`, so filters survive browser refresh

Do not introduce Tailwind, shadcn, styled-components, Bootstrap, or any CSS-in-JS unless the project's stack explicitly uses them.

## Before you design: read the existing files

If you are inside a codebase, always open `styles.css` and 1–2 existing page components before generating anything new. The goal is *consistency* — the new screen should feel like it belongs, not like a transplant.

Look for and reuse:

- **CSS custom properties** (design tokens on `:root`) — colors, radii, font families
- **Existing utility classes** — `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-sm`, `.input`, `.field`, `.form-row`, `.card`, `.page`, `.page-head`, `.data` (table), `.badge`, `.stat-card`, `.modal`, `.modal-backdrop`, `.toolbar`, `.filters`, `.empty-state`, `.spinner`
- **Layout patterns** — does the app use a top nav or sidebar? A two-column detail layout? Follow what exists.
- **Component conventions** — modal state pattern, panel slide-in vs modal, form submit pattern with `busy`/`error` state

If you cannot see the existing files and the request is non-trivial, ask the user to paste the `:root` block from `styles.css` and one existing page component before generating. This prevents a full revision cycle.

## Design language

When you have no existing reference, default to this. It is a clean, restrained, admin/fintech aesthetic.

### Color tokens

```css
:root {
  /* Brand */
  --ink: #3b2f8f;        /* primary — buttons, links, active states */
  --ink-deep: #251d63;   /* headings, sidebar background */
  --ink-soft: #ecebf7;   /* tint fills, hover states, badge backgrounds */

  /* Page */
  --paper: #f6f6f2;      /* page background */
  --surface: #ffffff;    /* cards, modals, panels */
  --border: #e2e1f0;     /* dividers, input borders */
  --muted: #6b6894;      /* secondary text, labels, placeholders */

  /* Semantic */
  --good: #1d7a55;       /* success, positive, received */
  --good-soft: #e8f5f0;
  --warn: #a05c10;       /* warning, pending, due */
  --warn-soft: #fdf3e3;
  --bad: #b03030;        /* error, danger, overdue */
  --bad-soft: #fdecea;

  /* Typography */
  --font-display: 'Bricolage Grotesque', sans-serif;  /* headings, numbers */
  --font-body: 'Inter', sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;            /* amounts, codes, dates */

  /* Shape */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}
```

Use only these variables — never hardcode hex values in component styles.

### Spacing

8px grid. Padding and gap values: 4 / 8 / 12 / 16 / 20 / 24 / 28 / 32. Do not use arbitrary values like 13px or 27px.

### Typography

- Display font (`--font-display`) for headings, stat card values, and large numbers
- Body font (`--font-body`) for all prose and UI labels at 15px base
- Mono font (`--font-mono`) for amounts, reference numbers, dates, codes
- Type scale (rem): 0.7 / 0.75 / 0.8 / 0.85 / 0.875 / 1 / 1.1 / 1.4 / 1.6 / 1.8
- Weights: 400 body, 500 medium, 600 semibold, 700 bold (display only)
- Amounts use `font-variant-numeric: tabular-nums`

### Shadows

Subtle only. Card: `0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)`. Modal: `0 20px 60px rgba(0,0,0,0.2)`. No glows, no heavy drops.

### Layout patterns

- **Page:** `.page` with `padding: 28px 32px`
- **Page header:** `.page-head` — flex row, title left, actions right
- **Stat cards:** `.stats-grid` with auto-fit columns, each card a `.stat-card` with `.label` + `.value`
- **Data tables:** `.data` — left-align text, right-align numbers, `--font-mono` for amounts, hover row highlight
- **Filters toolbar:** `.filters` — flex row of labeled select/input fields
- **Cards:** `.card` with `border-radius: var(--radius-md)` and `border: 1px solid var(--border)`
- **Modals:** `.modal-backdrop` → `.modal` (max-width 560px); `.modal-head` / `.modal-body` / `.modal-foot`
- **Slide-in panels:** fixed right panel (width ~440px) with backdrop — for add/edit flows that don't need a full page
- **Two-column detail:** `grid-template-columns: 320px 1fr` for detail pages (info panel left, main content right)
- **Timeline:** vertical thread with type-colored dot and card per entry — for activity logs, interaction histories
- **Empty state:** centered, short label, optional CTA button

## Icons

Icons live in `components/Icons.tsx` as inline SVGs using `currentColor`:

```tsx
const s = {
  viewBox: '0 0 24 24', width: 16, height: 16,
  fill: 'none', stroke: 'currentColor', strokeWidth: 2,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
};

export const IconPlus = () => <svg {...s}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>;
export const IconEdit = () => <svg {...s}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>;
export const IconTrash = () => <svg {...s}>...</svg>;
```

`currentColor` means the icon inherits the surrounding text colour — no inline fill/color props needed. Size via the `width`/`height` props on the shared `s` object: 14px inline with small text, 16px default, 20px for primary action buttons.

When adding icons for a new feature, append them to `Icons.tsx` — never import from an external library.

Standard icon set for admin modules:

| Context | Icon name suggestion |
|---------|----------------------|
| Add / New | `IconPlus` |
| Edit | `IconEdit` |
| Delete | `IconTrash` |
| Search | `IconSearch` |
| Close / Clear | `IconX` |
| Back | `IconArrowLeft` |
| Print | `IconPrint` |
| Approved / Done | `IconCheck` |
| Contacts / People | `IconContacts` / `IconTeam` |
| Phone / Call | `IconCall` |
| Email | `IconEmail` |
| Calendar / Date | `IconMeeting` |
| Note / Document | `IconNote` |
| Dashboard tiles | `IconDashboard` |
| Trending up | `IconTrendUp` |
| Alert / Reminder | `IconBell` |

One icon per button, one per section heading, one per row action. Do not decorate every label.

## Component patterns

### Buttons

```tsx
<button className="btn btn-primary">Save</button>
<button className="btn btn-ghost btn-sm">Cancel</button>
<button className="btn btn-danger btn-sm"><IconTrash /> Delete</button>
<button className="btn-icon"><IconEdit /></button>  {/* square icon-only */}
```

Always disable + show spinner while a form submission is in flight:

```tsx
<button className="btn btn-primary" onClick={submit} disabled={busy}>
  {busy ? <span className="spinner" /> : 'Save'}
</button>
```

### Forms

```tsx
<div className="field">
  <label>Company Name *</label>
  <input className="input" value={v} onChange={e => setV(e.target.value)} />
</div>
<div className="form-row">          {/* 2 columns */}
  <div className="field">...</div>
  <div className="field">...</div>
</div>
{error && <div className="error-text">{error}</div>}
```

Every form submit follows this exact pattern:

```tsx
const [busy, setBusy] = useState(false);
const [error, setError] = useState('');

async function submit() {
  setError(''); setBusy(true);
  try {
    await api('/api/resource', { method: 'POST', body: JSON.stringify(payload) });
    onDone();
  } catch (e: any) { setError(e.message); }
  finally { setBusy(false); }
}
```

### Badges / status chips

```tsx
<span className={`badge status-${record.status}`}>{record.status}</span>
```

Status class naming: `status-DRAFT`, `status-ACTIVE`, `status-PAID`, `status-WON`, etc. Define all in `styles.css` using semantic color variables. Never hardcode badge colors inline.

### Modal

```tsx
{editFor && (
  <Modal title="Edit Item" onClose={() => setEditFor(null)} footer={
    <>
      <button className="btn btn-primary" onClick={submit} disabled={busy}>
        {busy ? <span className="spinner" /> : 'Save'}
      </button>
      <button className="btn btn-ghost" onClick={() => setEditFor(null)}>Cancel</button>
      {error && <div className="error-text">{error}</div>}
    </>
  }>
    {/* form fields */}
  </Modal>
)}
```

Use the `xFor` pattern for modal state: `const [editFor, setEditFor] = useState<Item | null>(null)`. Modal only mounts when `editFor !== null`.

### Slide-in panel (add/edit flows)

For add/edit flows that don't warrant a full page, use a slide-in panel with a backdrop:

```tsx
<>
  <div className="panel-backdrop" onClick={onClose} />
  <div className="panel">
    <div className="panel-head"><h2>Add Lead</h2><button className="btn-icon" onClick={onClose}><IconX /></button></div>
    <div className="panel-body">/* fields */</div>
    <div className="panel-foot">/* actions */</div>
  </div>
</>
```

### Filterable list page

```tsx
// Filters in URL params, not component state
const [params, setParams] = useSearchParams();
const status = params.get('status') || '';

function setParam(key: string, value: string) {
  const next = new URLSearchParams(params);
  if (value) next.set(key, value); else next.delete(key);
  setParams(next, { replace: true });
}
```

### Data table structure

```tsx
<div className="card" style={{ padding: 0 }}>
  <table className="data">
    <thead>
      <tr><th>Name</th><th style={{ textAlign: 'right' }}>Amount</th><th>Status</th></tr>
    </thead>
    <tbody>
      {rows.map(r => (
        <tr key={r.id}>
          <td><Link to={`/resource/${r.id}`} style={{ fontWeight: 600 }}>{r.name}</Link></td>
          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
            ₹{Number(r.amount).toLocaleString('en-IN')}
          </td>
          <td><span className={`badge status-${r.status}`}>{r.status}</span></td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

Always right-align numeric columns. Use `var(--font-mono)` for amounts and reference numbers. Remove card padding when a table bleeds edge-to-edge.

### Stat card dashboard

```tsx
<div className="stats-grid">
  <div className="stat-card">
    <div className="label">Total Orders</div>
    <div className="value">{data.total}</div>
  </div>
  <div className="stat-card">
    <div className="label">Revenue</div>
    <div className="value good">₹{fmtMoney(data.revenue)}</div>
  </div>
</div>
```

Value color modifiers: `.value.good`, `.value.bad`, `.value.warn` — use them semantically (good = positive, bad = overdue/negative).

## Output structure

When fulfilling a design request, structure your response like this:

### 1. UI plan (2–5 bullets)

Name the key sections and any notable UX decisions. Keep it tight — this is orientation, not a spec document. Example: "Dashboard has 6 stat cards (total, active, low-stock, value, open orders, net balance), a recent-activity table, and a party-outstanding summary. Cards at the top in a 6-col grid."

### 2. Code

Provide complete, copy-pasteable output:

- **Page component** (`client/src/pages/PageName.tsx`) — full file including imports, types, and fetch logic
- **CSS additions** — append to `client/src/styles.css` with a clear section comment; never duplicate existing classes
- **Icon additions** — new exports to append to `client/src/components/Icons.tsx` if new icons are needed

Put each file in its own fenced code block with the file path as a comment or header.

### 3. Integration note (1–3 lines)

What to add to `App.tsx` (route), `Shell.tsx` (nav link), `server/src/index.js` (route registration), and the Prisma schema if the feature needs new data. Call out any new API endpoint the page depends on.

## What to avoid

- **Hardcoded colors** — use CSS variables only; never `color: #3b2f8f` inline in a component
- **Arbitrary spacing** — stick to the 8px grid; no `padding: 13px` or `margin: 27px`
- **Inconsistent radius** — `--radius-sm` for inputs and badges, `--radius-md` for cards and modals
- **Heavy shadows or gradients** — restraint reads as quality in business software
- **Random icon density** — one icon per button, not one per label
- **Mobile afterthought** — use CSS that works at narrow widths; stack cards and make tables scrollable below `768px`
- **`any` state types** — always define the type at the top of the file; no `useState<any>`
- **Inline `fetch()`** — always use `api<T>()` from `lib/api.ts`
- **Multiple CSS files per feature** — all styles go into `styles.css`, scoped with a page or component class prefix (`.leads-...`, `.team-...`)
- **Generic empty states** — write specific copy ("No leads yet. Add your first lead to get started.") not "No data found."

## Handling ambiguity

If the request is under-specified ("design the reports page"), make reasonable assumptions and state them up front in the UI plan — one line each, no long preamble. Example: "Assuming: sales report shows date-range filter, total revenue, units sold, top 5 customers by value, and a monthly trend bar (CSS only)."

Ask when the answer genuinely changes the structure — e.g. "Is this a standalone page or a modal on top of the list?" Do not ask about things you can reasonably decide (color choices, icon selection, column order).

## Worked example

**Request:** "Design the Team management page"

**UI plan:**
- List of team members in a card-padded table (avatar initials, name, email, role badge, join date, edit/delete actions)
- Empty state with a CTA button when no members exist
- "Add Member" opens a Modal with name, email, password fields and an info note about member access
- Admin-only page — redirects non-admins to `/dashboard`

**Code:** `client/src/pages/Team.tsx` — full file with `Member` type, `useEffect` fetch, `MemberModal` sub-component, `deleteMember` confirm flow.

**CSS additions:** avatar circle pattern (`.avatar-circle`) appended to `styles.css`.

**Integration:** add `<Route path="/team" element={<Team />} />` in `App.tsx`; add Team `NavLink` to `Shell.tsx` wrapped in `{user?.role === 'ADMIN' && ...}`; no new server route needed beyond `/api/team` (already in server).

That is the shape — concrete, consistent with the stack, visually restrained, immediately usable.
