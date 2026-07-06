This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Running on low-memory Windows laptops (8GB RAM)

Next.js 16 uses **Turbopack by default** for `next dev`, even with no flags — and on an 8GB
Windows machine its dev-time memory footprint can grow large enough to freeze the laptop.
`npm run dev` in this project explicitly passes `--webpack` for that reason; only
`npm run dev:turbo` opts into Turbopack. Prefer `npm run dev` unless you have RAM to spare.

If `node.exe` is still consuming too much memory or the terminal has frozen, reset cleanly:

```powershell
taskkill /F /IM node.exe
Remove-Item -Recurse -Force .next
npm run dev
```

Other things that help on an 8GB machine:
- Close duplicate dev servers — check Task Manager for more than one lingering `node.exe`
  before starting a new one.
- If memory climbs over a long session even without a freeze, `npm run fresh` (clears `.next`
  and restarts) is usually enough without a full `taskkill`.
- Avoid `npm run dev:turbo` for day-to-day work and demos; it's there for when you specifically
  want to benchmark or debug Turbopack itself.
