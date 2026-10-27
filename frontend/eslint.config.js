import react from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import globals from "globals";
import shared from "../.crepidoma/configs/eslint.config.js";

export default [
  ...shared,
  { ignores: ["dist/**", "coverage/**"] },
  {
    files: ["src/**/*.{ts,tsx}", "tests/**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
  },
  { files: ["vite.config.ts", "eslint.config.js"], languageOptions: { globals: globals.node } },
  jsxA11y.flatConfigs.recommended,
  react.configs.flat["recommended-latest"],
  {
    // TanStack Virtual returns functions React Compiler cannot memoise; we do not use the compiler.
    rules: { "react-hooks/incompatible-library": "off" },
  },
];
