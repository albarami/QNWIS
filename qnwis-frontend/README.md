# QNWIS Enterprise Frontend

**Status**: Phase 1 Complete - Project Structure Created  
**Next**: Install dependencies and start development

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
qnwis-frontend/
├── src/
│   ├── main.tsx          # Entry point
│   ├── App.tsx           # Root component
│   ├── index.css         # Global styles
│   └── types/            # TypeScript definitions (Phase 2)
├── package.json          # Dependencies
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript config (strict mode)
└── tailwind.config.js    # TailwindCSS config
```

## Tech Stack

- **React 19** - Latest React with concurrent rendering
- **TypeScript 5.9** - Strict mode enabled
- **Vite 7.2** - Lightning-fast dev server
- **TailwindCSS 3.4** - Utility-first CSS
- **@microsoft/fetch-event-source** - SSE client

## Implementation Phases

- [x] Phase 1: Project structure (COMPLETE)
- [ ] Phase 2: Types & SSE connection
- [ ] Phase 3: Workflow visualization
- [ ] Phase 4: Live agent streaming
- [ ] Phase 5: Debate visualization
- [ ] Phase 6: Critique visualization
- [ ] Phase 7: Results display
- [ ] Phase 8: Error handling
- [ ] Phase 9: Integration testing
- [ ] Phase 10: Polish & deploy

## Backend Connection

**Backend URL**: `http://localhost:8000/api/v1/council/stream`  
**Port**: Frontend runs on 3000, Backend on 8000  
**CORS**: Already configured in backend
