# Steering Best Practices

## For the Reviewer Agent
You maintain these steering files. Follow these rules:

### Keep Files Focused
One domain per file. Don't mix API patterns with testing conventions.

### Use Clear Names
- `conventions.md` — code patterns and import organization
- `testing.md` — test fixtures, mocking, organization
- `status.md` — project state, file tree, progress
- `issues.md` — problems and suggestions
- `code-quality.md` — formatting, linting, style

### Include Context
Explain WHY decisions were made, not just what the standards are. If the team chose a pattern, note the reason.

### Provide Examples
Use short code snippets from the ACTUAL codebase. Before/after comparisons when suggesting changes.

### Security
Never include API keys, tokens, or secrets in steering files. These are part of the codebase.

### Keep It Concise
Every steering file is loaded into agent context. Verbose files waste context window. Aim for under 50 lines per file.

### Be Factual
Document what IS in the code, not what should be. Flag gaps in issues.md, don't editorialize in other files.
