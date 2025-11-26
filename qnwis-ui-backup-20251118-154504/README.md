# QNWIS React Streaming Console

Modern React + TypeScript frontend for the Qatar National Workforce Intelligence System (QNWIS).  
The app renders the ministerial streaming console, consumes Server-Sent Events (SSE) from
`/api/v1/council/stream`, and visualises every stage of the LangGraph workflow (classification,
agent execution, debate/critique, synthesis, and verification).

## Features

- **SSE-native workflow viewer** powered by `@microsoft/fetch-event-source`
- **Stage-aware layouts** (classification, orchestration, analysis) with optimistic progress UI
- **Shared component library** under `src/components/{common,workflow,analysis}`
- **Tailwind CSS + Lucide icons** for consistent Qatar MoL design language
- **Simple configuration**: Vite proxy points `/api/*` to the FastAPI server on `http://localhost:8000`

## Project Structure

| Path                           | Purpose |
|--------------------------------|---------|
| `src/App.tsx`                  | Root layout and page orchestration |
| `src/components/common/*`      | Buttons, cards, badges, spinners, error boundaries |
| `src/components/workflow/*`    | Stage indicator, metadata panel, query input |
| `src/components/analysis/*`    | Debate, critique, extracted facts, KPI cards |
| `src/hooks/useWorkflowStream`  | SSE client that maps backend `StreamEventResponse` ➜ UI state |
| `src/types/workflow.ts`        | Shared TypeScript types mirroring backend Pydantic models |
| `src/utils/cn.ts`              | Small helper for Tailwind class concatenation |

## Requirements

- Node.js **18.x** or newer
- npm **10.x** (ships with Node 18)
- Running QNWIS backend (`uvicorn src.qnwis.api.server:app --port 8000`)

## Getting Started

```bash
cd qnwis-ui
npm install            # install dependencies once
npm run dev -- --host 0.0.0.0 --port 3000
```

Open http://localhost:3000. The Vite dev server proxies `/api/*` calls to `http://localhost:8000`
(`vite.config.ts`), so no extra environment variables are required during development.

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev`     | Start Vite dev server with Fast Refresh |
| `npm run build`   | Type-check (`tsc -b`) and produce production bundle in `dist/` |
| `npm run preview` | Serve the built bundle locally (useful for smoke tests) |
| `npm run lint`    | Run ESLint with the project configuration |

## Backend Integration & SSE Contract

The hook `useWorkflowStream` posts `{question, provider}` to `/api/v1/council/stream` and expects
the backend `StreamEventResponse` schema defined in `src/qnwis/api/models/responses.py`. The hook
handles:

- connection lifecycle (`onopen`, `onmessage`, `onerror`, `onclose`)
- incremental synthesis tokens (`payload.token`) during the `synthesize` stage
- status transitions (`running` ➜ `complete` / `error`)

If you change the backend payload, update:

1. `src/types/workflow.ts` (TypeScript definitions)
2. `src/hooks/useWorkflowStream.ts` (state mapper)
3. Any components that consume the fields you added/removed

## Styling & Theming

- Tailwind is configured via `tailwind.config.js` and `src/index.css`
- Global styles live in `src/App.css`
- Component-specific styles are expressed through Tailwind utility classes to keep the bundle lean

To add Qatar-specific color tokens, extend the `theme.colors` block in `tailwind.config.js`.

## Production Build & Deployment

```bash
npm run build
# dist/ contains static assets (index.html + hashed JS/CSS)
```

Serve the `dist/` directory behind any static host (Nginx, S3/CloudFront, etc.) and point the proxy
for `/api/*` to the deployed FastAPI service. If you need a different backend URL at runtime, update
`vite.config.ts` or add `VITE_API_BASE` and use `import.meta.env.VITE_API_BASE` inside the hook.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `npm run dev` cannot find backend | Start the FastAPI server on `http://localhost:8000` or change the proxy target in `vite.config.ts`. |
| SSE stops prematurely | Ensure `council_llm.py` emits well-formed JSON per `StreamEventResponse`. Use browser dev tools → Network → EventStream to inspect payloads. |
| Type errors referencing backend payload keys | Regenerate or update `src/types/workflow.ts` to match the latest backend schema, then rerun `npm run build`. |

For deeper integration details, see `REACT_MIGRATION_REVISED.md` (Phase 2–6) and
`BACKEND_SSE_STATUS.md` for the server contract.
