# src

Application code.

1. `main.tsx`: mounts the app and loads the stylesheets.
2. `favicon.svg`: tab icon and logo geometry; Vite hashes it into `/assets/`.
3. `App.tsx`: query client, tooltip provider, route table and the app shell; the masthead holds the centred logo and the top-right About link.
4. `api/`: typed API client, response types, query hooks and job polling.
5. `lib/`: pure helpers and small hooks.
6. `components/`: shared UI.
7. `pages/`: one component per route.
8. `styles/`: design tokens and plain CSS.
