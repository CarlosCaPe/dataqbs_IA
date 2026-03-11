---
name: workspace-skill-discovery
description: >
  MANDATORY at session start: discover and load ALL skills across the workspace.
  Never rely only on global ~/.claude/skills/. Always scan for project-level
  .claude/skills/ folders in every repo and sub-project.
metadata:
  short-description: Discover all workspace skills
  priority: always
---

# Workspace Skill Discovery

## Rule (MANDATORY)

**Before listing available skills or starting any complex task**, run this discovery:

```bash
# 1. Find ALL skill locations in workspace
find <workspace_folders> -type d -name "skills" -path "*/.claude/*" 2>/dev/null

# 2. Count skills per location
for d in $(find <workspace_folders> -type d -name "skills" -path "*/.claude/*" 2>/dev/null); do
  echo "$d: $(find "$d" -maxdepth 1 -type d | tail -n +2 | wc -l) skills"
done
```

## Skill Hierarchy (4 levels)

| Level | Location | Scope | Auto-loaded? |
|-------|----------|-------|--------------|
| 1. Global | `~/.claude/skills/` | All sessions, all repos | Yes (Claude Code/Codex) |
| 2. Repo root | `<repo>/.claude/skills/` | Entire repo | Yes (Claude Code/Codex) |
| 3. Project-level | `<repo>/projects/<name>/.claude/skills/` | Specific project | Read on demand |
| 4. Legacy custom | `<repo>/skills/` (no .claude) | Manual only | No — migrate to level 2 |

## Key Rule

**Never list only global skills.** Always search the filesystem for project-level skills.
Project skills contain the most valuable, context-specific workflows (CV updates, deploy pipelines, DB patterns, security audits).

## When adding skills

- Use `.claude/skills/<name>/SKILL.md` format everywhere
- If a skill applies to multiple projects, put it at level 2 (repo root)
- If it's project-specific, put it at level 3
- Global (level 1) is for curated/installed skills only
