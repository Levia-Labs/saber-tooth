import { readFileSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const BACKEND = "http://127.0.0.1:8100";
const OUT = fileURLToPath(new URL("../src/saber_tooth/web", import.meta.url));

/** Remove only previous build output so the committed README.md in the folder survives. */
function cleanBuildOutput(): Plugin {
  let outDir = OUT;
  return {
    name: "clean-build-output",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
    },
    buildStart() {
      for (const name of ["assets", "index.html", "favicon.svg"]) {
        rmSync(`${outDir}/${name}`, { recursive: true, force: true });
      }
    },
  };
}

/** Vendor chunks: React and the router, TanStack, and Radix stay cached across app releases. */
function manualChunks(id: string): string | undefined {
  if (!id.includes("node_modules")) return undefined;
  if (/node_modules\/@radix-ui\//.test(id)) return "radix";
  if (/node_modules\/@tanstack\//.test(id)) return "tanstack";
  return "react";
}

// The release version lives in pyproject.toml; frontend/package.json stays 0.0.0 and is never released.
const PYPROJECT = readFileSync(
  fileURLToPath(new URL("../pyproject.toml", import.meta.url)),
  "utf8",
);
const APP_VERSION = /^version\s*=\s*"([^"]+)"/m.exec(PYPROJECT)?.[1] ?? "unknown";

const proxy = { target: BACKEND, changeOrigin: true, headers: { Host: "127.0.0.1:8100" } };

export default defineConfig({
  plugins: [react(), cleanBuildOutput()],
  base: "/",
  define: { __APP_VERSION__: JSON.stringify(APP_VERSION) },
  build: {
    outDir: OUT,
    emptyOutDir: false,
    sourcemap: false,
    target: "es2022",
    rollupOptions: { output: { manualChunks } },
  },
  server: { port: 5173, proxy: { "/api": proxy, "/mcp": proxy } },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    css: false,
    // Half the cores: every worker cold-compiles the lazy pages, and a full fan-out starved them
    // past the 5 s asyncUtilTimeout.
    maxWorkers: "50%",
    testTimeout: 15_000,
  },
});
