# Mahoosuc OS Product Page Design

**Date:** 2026-03-22
**Status:** Approved
**Owner:** Mahoosuc Solutions product team

---

## Objective

Build a public-facing product page for the Mahoosuc Operating System within the existing `web/` Next.js 14 app. The page tells the story of an event-driven AI operating system that manages life, businesses, and properties — grounded in code-validated metrics and real portfolio evidence.

## Brand Architecture

```
Grateful House Inc. (parent company)
  Mahoosuc Solutions (IT services company)
    Mahoosuc Operating System (the AI infrastructure platform)
      Agent Jumbo (orchestration engine)
      AG Mesh (event-driven backbone, Redis Streams)
      DevFlow (AI software delivery — turns specs into code via agent orchestration)
      ArchitectFlow (requirements generation & system design)
      ContentStudio (content generation & marketing)
      [Additional named solutions TBD — discovered by SaaS Specialist Agent]
      414+ Commands / Skills / SOPs (the agent instruction set)
```

**Color identity:** Copper (#B87333) and Blue (#1E3A5F), dark mode default.

## Target Audiences

Two audiences with a path-splitting entry point:

1. **Technical founders / CTOs** evaluating agent platforms (vs Dify, CrewAI, LangGraph, n8n)
2. **Small business owners** who want AI automation for operations (properties, finance, scheduling)

## Specialized Agent Team

Four agents run in parallel to generate structured outputs:

### Agent 1: Product Marketing Specialist

- **Mandate:** Develop the Mahoosuc OS narrative, hero copy, value propositions, section headlines, path-fork messaging
- **Inputs:** Brand hierarchy, competitive positioning docs, README, GitHub portfolio (26 repos across healthcare, hospitality, home-services, AI infrastructure, community)
- **Output:** `docs/product-page/marketing-content.md`
- **Output structure:** Sections with H2 headers: Hero (headline, subtitle, CTAs), Path Fork (builder card, business card), Platform Story (3 paragraphs), Solution Headlines (per product), Proof Point Captions, Portfolio Blurbs, How It Works Narrative, Pricing Intro, Final CTA

### Agent 2: SaaS Product Specialist

- **Mandate:** Map 36 instruments + 84 tools + 26 repos into named product groupings. Define what each product does, what code backs it, how they interconnect through AG Mesh
- **Inputs:** Full instrument inventory, tool registry, GitHub repos, AG Mesh architecture (agentmesh_bridge.py, agentmesh_task_handler.py, agentmesh_risk.py)
- **Output:** `docs/product-page/product-catalog.json`
- **Output schema:**

```json
{
  "products": [
    {
      "slug": "devflow",
      "name": "DevFlow",
      "tagline": "one-liner",
      "description": "2-3 sentence description",
      "audience": "builder" | "business" | "both",
      "instruments": ["workflow_engine", "deployment_orchestrator"],
      "tools": ["devops_deploy", "code_review"],
      "repos": ["agent-jumbo"],
      "integrations": ["Linear", "GitHub Actions"],
      "ag_mesh_events": ["task.assigned", "task.completed"],
      "icon_suggestion": "description for icon"
    }
  ],
  "naming_rationale": "explanation of naming decisions",
  "interconnections": [
    { "from": "architectflow", "to": "devflow", "event": "spec.approved", "description": "..." }
  ]
}
```

### Agent 3: Financial Validation Agent

- **Mandate:** Model pricing tiers from actual cost structure — LLM tokens, compute (Docker/GPU), storage (SQLite per instrument), integration API costs (Stripe, Twilio, Linear, etc.)
- **Inputs:** Integration list, LLM router config, infrastructure requirements, competitive pricing landscape
- **Output:** `docs/product-page/pricing-model.json`
- **Output schema:**

```json
{
  "cost_components": [
    { "name": "LLM tokens", "unit": "per 1M tokens", "cost_low": 0.25, "cost_high": 15.00, "notes": "varies by model" }
  ],
  "tiers": [
    {
      "name": "Starter",
      "price_monthly": 0,
      "tagline": "one-liner",
      "includes": ["list of features"],
      "limits": { "commands_per_month": 1000, "instruments": 5 },
      "cost_basis": "explanation of why this price"
    }
  ],
  "competitive_reference": [
    { "competitor": "Dify", "tier": "Pro", "price": 59, "comparison_notes": "..." }
  ],
  "assumptions": ["list of assumptions made"]
}
```

### Agent 4: Code Introspection Agent

- **Mandate:** Build validation manifest by scanning codebase and GitHub — tools, endpoints, instruments, integrations, test coverage, lines of code
- **Inputs:** The actual codebase + GitHub API
- **Output:** `docs/product-page/platform-manifest.json`

## Code Introspection Engine

### Build-Time Manifest

`scripts/build-platform-manifest.sh` is a shell script that:

1. Runs the Python introspection logic via `python3 scripts/introspect_platform.py`
2. Merges product catalog data from `docs/product-page/product-catalog.json` into the `products` field
3. Writes output to `web/public/platform-manifest.json`

**Build integration:** Added as a `prebuild` npm script in `web/package.json`:

```json
{
  "scripts": {
    "prebuild": "cd .. && bash scripts/build-platform-manifest.sh",
    "build": "next build"
  }
}
```

**Failure mode:** If the script fails (Python not available, file errors), it falls back to the last committed `web/public/platform-manifest.json`. The manifest is committed to git as a baseline — the prebuild script overwrites it with fresh data when available.

**Git strategy:** `web/public/platform-manifest.json` is tracked in git. The prebuild script updates it. CI commits the updated manifest if it changes.

**Manifest schema (all values dynamically generated — examples below are illustrative):**

```json
{
  "generated_at": "ISO-8601 timestamp",
  "platform": {
    "commands": { "total": 0, "categories": 0 },
    "instruments": { "total": 0, "active": 0 },
    "tools": { "total": 0 },
    "api_endpoints": { "total": 0 },
    "integrations": [],
    "helper_modules": 0
  },
  "github": {
    "repos": 0,
    "verticals": []
  },
  "ag_mesh": {
    "event_types": [],
    "risk_levels": [],
    "agent_profiles": 0
  },
  "products": []
}
```

### Live API Layer

`/api/platform-status` is a **Next.js API route** (not a Python endpoint) that proxies to the existing backend health endpoints (`/health`, `/api/gateway/status`). It aggregates responses into a status summary. If the backend is unreachable, it returns `{ "live": false }` and the UI falls back gracefully to build-time metrics only.

**Fallback UI:** When live API is unreachable, metrics display with a subtle "(as of build date)" label. No spinners, no error states — the build-time data is always the baseline.

### Validation Principle

No number on the product page exists without a code path that generates it. If the codebase changes, the next build updates the claims automatically.

## Infrastructure Prerequisites

### B1: Middleware Update

The current `web/middleware.ts` only exempts `/login`, `/api/`, `/_next/`, and `/favicon` from auth. All `(public)` routes must be accessible without authentication.

**Fix:** Add public route paths to the middleware exemption list:

```typescript
const publicPaths = [
  '/login',
  '/',           // landing page
  '/platform',
  '/solutions',
  '/portfolio',
  '/pricing',
  '/demo',
  '/documentation',
]
```

The `(public)` route group is a Next.js filesystem convention for layout nesting — it does NOT bypass middleware. The middleware must explicitly exempt these paths.

### B2: Tailwind Color Tokens

Add Mahoosuc brand colors to `web/tailwind.config.ts`:

```typescript
colors: {
  copper: {
    50: '#fdf5ef',
    100: '#fae8d8',
    200: '#f4cdb0',
    300: '#edac7e',
    400: '#e4854a',
    500: '#B87333',  // primary copper
    600: '#9a5d28',
    700: '#7c4a22',
    800: '#5e381c',
    900: '#3f2613',
  },
  'mahoosuc-blue': {
    50: '#eef3f8',
    100: '#d5e0ed',
    200: '#a8c0d9',
    300: '#7a9fc4',
    400: '#4d7faf',
    500: '#1E3A5F',  // primary blue
    600: '#1a3254',
    700: '#162a48',
    800: '#12223c',
    900: '#0e1a30',
  },
}
```

**Accessibility note:** Copper (#B87333) on deep blue (#1E3A5F) has ~2.8:1 contrast ratio, which fails WCAG AA for body text. Copper must be used for accents, borders, and large headings only. Body text on dark backgrounds uses white/slate-200 for AA compliance. All text combinations must meet 4.5:1 minimum contrast.

### B3: Dark Mode Default

The product page layout (`web/app/(public)/layout.tsx`) applies the `dark` class to `<html>` by default. No light mode toggle on the product page — it is dark-only for the marketing site. The internal dashboard retains its existing theme toggle.

```tsx
// web/app/(public)/layout.tsx
export default function PublicLayout({ children }) {
  return (
    <html lang="en" className="dark">
      {/* ... */}
    </html>
  )
}
```

Note: Since the (public) layout is separate from the (app) layout, this does not affect the internal dashboard's theming.

## Page Structure

### Routes

```
web/app/(public)/
  page.tsx                    -- Hero + Path Fork (replaces current, old components preserved)
  platform/page.tsx           -- Full platform map (AG Mesh visual)
  solutions/page.tsx          -- Named products grid
  solutions/[slug]/page.tsx   -- Individual product deep-dive
  portfolio/page.tsx          -- Real projects built on the platform
  pricing/page.tsx            -- Cost-model-driven tiers
  demo/page.tsx               -- Already exists, enhance
```

**Rollback:** The existing `HeroSection.tsx`, `FeaturesGrid.tsx`, and `CTASection.tsx` components are preserved (not deleted). The new `page.tsx` replaces their usage but they remain available if rollback is needed. No feature flag needed — git revert is sufficient.

### Sections (top-level page.tsx, scrolling with route breakouts)

1. **Hero** — Copper/blue gradient background. Headline, subtitle with live metric count from manifest, two CTAs: "Get Demo" / "View Platform."

2. **Path Fork** — Side-by-side cards:
   - "I'm Building AI Products" -> platform architecture, DevFlow, ArchitectFlow, API surface, agent profiles
   - "I Want AI Running My Business" -> property management, finance, scheduling, customer lifecycle, automations

3. **Platform Map** — SVG-based static diagram (not interactive in v1) showing AG Mesh at center with named products as nodes. Implemented as a React component rendering inline SVG with Tailwind classes. Clicking a node navigates to `/solutions/[slug]`. Responsive: horizontal layout on desktop, vertical stack on mobile. Data sourced from the `products` array in platform-manifest.json (populated by merging product-catalog.json during build).

4. **Named Solutions** — Card grid of each product. Each card: name, one-liner, backing instrument count, key integrations, link to `/solutions/[slug]`.

5. **Proof Points** — Metrics strip from manifest: tool count, endpoint count, integrations, test pass rate, agent profiles. Each number links to the GitHub repo or relevant docs page.

6. **Portfolio Showcase** — Top 4 projects shown by default with "View all" link to `/portfolio`. Default visible: HDIM (healthcare), West Bethel Motel (hospitality), BolducBuilders (home services), CommandBridge (operations). Chosen for vertical diversity.

7. **How It Works** — Three-step visual: ArchitectFlow (design) -> DevFlow (build) -> AG Mesh (orchestrate).

8. **Pricing** — Tiers from Financial Validation Agent, grounded in real cost modeling.

9. **CTA** — Demo request form + self-hosted install instructions.

### SEO & Metadata

Each route exports `generateMetadata()` with:

- Title: "Mahoosuc OS | [page-specific subtitle]"
- Description: Unique per page, incorporating key metrics
- Open Graph: title, description, image (static OG image in copper/blue branding)
- Structured data: JSON-LD `SoftwareApplication` schema on the landing page

Performance targets: LCP < 2.5s, CLS < 0.1 (standard Core Web Vitals thresholds).

### Design Language

- Dark mode only (product page) with copper (#B87333) accent and deep blue (#1E3A5F) secondary
- White/slate-200 for body text (WCAG AA compliant on dark backgrounds)
- Copper for accents, borders, large headings, CTAs
- Clean typography — monospace for metrics/code/IDs, sans-serif for prose
- Existing Tailwind v3 + Radix UI primitives (already in project)
- No framework migration required for this phase

## Implementation Phases

### Phase 1: Agent Discovery (parallel)

All 4 specialized agents run simultaneously, producing structured outputs to `docs/product-page/`.

### Phase 2: Review & Refine

- Review agent outputs against defined schemas
- Finalize product names and code mappings
- Validate pricing model assumptions
- Confirm introspection metrics match manual counts
- Review marketing copy for accuracy against codebase

### Phase 3: Build

- Infrastructure prerequisites (middleware update, Tailwind tokens, dark mode layout)
- Introspection script (`scripts/build-platform-manifest.sh` + `scripts/introspect_platform.py`)
- Product page routes and components
- Platform map SVG component
- Live API status Next.js route
- Portfolio showcase with GitHub data
- SEO metadata and OG images

### Phase 4: Next.js Upgrade (follow-on, separate spec)

- Plan and execute 14 -> 16 migration for full web/ app
- Adopt Cache Components for product page (static shell + dynamic metrics)
- Migrate middleware.ts to proxy.ts (Next.js 16 rename)

## Out of Scope

- Building new instruments or tools
- Changing the backend Python codebase (except the introspection script which reads only)
- Production deployment (separate conversation)
- Building actual named product UIs (ArchitectFlow app, etc.)
- Next.js 14 -> 16 migration (Phase 4, separate spec)
- Interactive/animated platform map (v1 is static SVG; interactivity is a follow-on)

## Success Criteria

1. Product page renders with real metrics from platform-manifest.json
2. Every number on the page traces to a code path that generates it
3. Named products map to specific instruments, tools, and repos
4. Pricing tiers are grounded in measured cost components
5. Both audience paths (Builder / Business Owner) have complete content
6. Portfolio section shows real GitHub repos with accurate descriptions
7. Page renders correctly in dark mode with copper/blue identity
8. All public routes are accessible without authentication
9. All text meets WCAG AA contrast ratio (4.5:1 minimum)
10. LCP < 2.5s, CLS < 0.1
11. SEO metadata and JSON-LD structured data present on all routes

## Key Files Reference

- Existing public page: `web/app/(public)/page.tsx`
- Middleware (needs update): `web/middleware.ts`
- Tailwind config (needs tokens): `web/tailwind.config.ts`
- AG Mesh bridge: `python/helpers/agentmesh_bridge.py`
- AG Mesh task handler: `python/helpers/agentmesh_task_handler.py`
- AG Mesh risk: `python/helpers/agentmesh_risk.py`
- Competitive positioning: `docs/COMPETITIVE_POSITIONING_V1.md`
- Competitive analysis: `COMPETITIVE-ANALYSIS.md`
- Mahoosuc tools: `docs/MAHOOSUC_TOOLS.md`
- Existing hero: `web/components/HeroSection.tsx`
- Existing features: `web/components/FeaturesGrid.tsx`
- Package.json: `web/package.json` (Next.js 14, React 18, Tailwind v3)
