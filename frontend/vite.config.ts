import { rmSync } from "node:fs";
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

const proxy = { target: BACKEND, changeOrigin: true, headers: { Host: "127.0.0.1:8100" } };

export default defineConfig({
  plugins: [react(), cleanBuildOutput()],
  base: "/",
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
  },
});
