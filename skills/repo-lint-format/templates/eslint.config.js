// Framework default ESLint flat config for a TypeScript project.
// Order matters: each config can override rules from the ones before it.
// eslint-config-prettier must stay last — see SKILL.md's "ESLint" section.
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier/flat';
// Remove this import (and the config entry below) for a backend-only
// project with no React frontend — see SKILL.md.
import reactHooks from 'eslint-plugin-react-hooks';

export default defineConfig([
  {
    files: ['**/*.{js,ts,tsx}'],
    extends: [
      js.configs.recommended,
      // strictTypeChecked + stylisticTypeChecked is typescript-eslint's
      // own maximum type-aware coverage — each already includes
      // recommended's rules, so don't also list recommended/
      // recommendedTypeChecked here.
      tseslint.configs.strictTypeChecked,
      tseslint.configs.stylisticTypeChecked,
      reactHooks.configs.flat.recommended,
      eslintConfigPrettier,
    ],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    // This config file itself isn't covered by tsconfig.json's own
    // `include`, so type-aware rules above have no type information for
    // it — type-check everything else, not this file.
    files: ['eslint.config.js'],
    extends: [tseslint.configs.disableTypeChecked],
  },
]);
