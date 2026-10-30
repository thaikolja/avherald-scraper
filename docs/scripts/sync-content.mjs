import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, join }               from 'node:path'
import { fileURLToPath }               from 'node:url'

const root      = join(dirname(fileURLToPath(import.meta.url)), '../..')
const changelog = readFileSync(join(root, 'CHANGELOG.md'), 'utf8').replace(/^# Changelog\n+/, '')
const config    = readFileSync(join(root, 'config.ini'), 'utf8')

const frontmatter = `---
title: Changelog
description: What changed in The Aviation Herald Scraper.
navigation:
  icon: i-lucide-history
---

This page is copied from \`CHANGELOG.md\` when the documentation is built.

`

writeFileSync(join(root, 'docs/content/4.project/2.changelog.md'), frontmatter + changelog)

const configPage = `---
title: config.ini
description: The settings file, copied from the repository at build time.
navigation:
  icon: i-lucide-file-cog
---

This page is copied from the repository \`config.ini\` when the documentation is built. Command-line flags still override these values.

\`\`\`ini [config.ini]
${config.trim()}
\`\`\`
`

writeFileSync(join(root, 'docs/content/3.reference/4.config-ini.md'), configPage)
