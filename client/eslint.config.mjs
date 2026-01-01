import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Allow 'any' types - disable TypeScript any rule
      "@typescript-eslint/no-explicit-any": "off",

      // Allow unused variables (useful during development)
      "@typescript-eslint/no-unused-vars": "warn",

      // Allow unescaped entities in JSX (common with apostrophes)
      "react/no-unescaped-entities": "off",

      // Make useEffect dependencies less strict
      "react-hooks/exhaustive-deps": "warn",

      // Allow setState in effects (sometimes necessary)
      "react-hooks/set-state-in-effect": "warn",

      // Allow img tags (Next.js Image can be restrictive)
      "@next/next/no-img-element": "warn",
    },
  },
]);

export default eslintConfig;
