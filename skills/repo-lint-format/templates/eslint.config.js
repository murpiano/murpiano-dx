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

export default defineConfig({
  files: ['**/*.{js,ts,tsx}'],
  extends: [
    js.configs.recommended,
    tseslint.configs.recommended,
    tseslint.configs.recommendedTypeChecked,
    reactHooks.configs.flat.recommended,
    eslintConfigPrettier,
  ],
  languageOptions: {
    parserOptions: {
      projectService: true,
    },
  },
});
