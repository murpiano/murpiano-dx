// Framework default lint-staged config. lint-staged runs each file's
// matching command list in order and only proceeds past eslint --fix
// to prettier --write if eslint exits 0; it re-stages whatever either
// command changed. See SKILL.md's "Pre-commit hook" section.
export default {
  '*.{js,ts,tsx}': ['eslint --fix', 'prettier --write'],
};
