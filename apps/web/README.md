# MemoryOps AI — Web

Next.js (App Router) + Tailwind frontend: landing, chat demo, memory dashboard,
admin/audit, and architecture pages.

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                         # http://localhost:3000
```

Pages: `app/page.tsx` (landing), `app/chat`, `app/memories`, `app/admin`,
`app/architecture`. API client: `lib/api.ts`.
