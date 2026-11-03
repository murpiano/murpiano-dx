# npm publishing

1. Verify `npm pack --dry-run` contains only runtime files.
2. Keep `package.json` version equal to the GitHub release tag without the `v` prefix.
3. Configure the `NPM_TOKEN` GitHub Secret. Never place it in the repository or logs.
4. Publish only after the GitHub Release and CI checks succeed.
5. Use `npm publish --access public` from the release workflow.

The package exposes the `murpiano-dx` command through `bin/murpiano-dx.js`. The
launcher delegates to the framework's existing Bash entry point, so npm and the
repository installation use the same setup and restore behavior.
