# SkillsMP CLI

Search, discover, and install agent skills from [skillsmp.com](https://skillsmp.com).

## Setup

### 1. Get API Key
1. Go to https://skillsmp.com/auth/login
2. Generate your API key
3. Configure it:

```bash
# Option A: Environment variable
export SKILLSMP_API_KEY=sk_live_your_key_here

# Option B: Config file
python cli.py config --set-key sk_live_your_key_here
# Saves to ~/.skillsmp/config.yaml
```

### 2. Create Shell Alias (optional)
Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias skillsmp='python ~/Documents/github/dataqbs_IA/tools/skillsmp/cli.py'
```

## Usage

### Search Skills (keyword)
```bash
skillsmp search "code review" --limit 10 --sort stars
skillsmp search "pdf" --sort recent
```

### AI Semantic Search
```bash
skillsmp ai-search "how to automate code reviews with AI"
skillsmp ai-search "best practices for web scraping"
```

### Install Skill
```bash
# Install globally (all projects)
skillsmp install https://github.com/user/repo --global

# Install to current project only
skillsmp install https://github.com/user/repo --project
```

### Check Quota
```bash
skillsmp quota
# Shows remaining API calls (500/day)
```

## Installation Locations

| Flag | Path | Scope |
|------|------|-------|
| `--global` (default) | `~/.claude/skills/<name>/` | All projects |
| `--project` | `.claude/skills/<name>/` | Current project only |

## Rate Limits

- 500 requests per day per API key
- Resets at midnight UTC
- Headers show remaining quota after each request

## Dependencies

- Python 3.8+
- `git` for cloning repos
- Optional: `pyyaml` for config file (falls back to simple parsing)

## File Structure

```
~/.claude/skills/           # Global skills (available everywhere)
    skillsmp/SKILL.md       # This integration skill
    <installed-skill>/

~/.skillsmp/
    config.yaml             # API key storage

.claude/skills/             # Project-level skills (per-repo)
    <project-skill>/
```

## Examples

```bash
# Find popular code review skills
skillsmp search "code review" --limit 5 --sort stars

# Semantic search for specific use case
skillsmp ai-search "automate GitHub PR reviews with AI"

# Install a skill globally
skillsmp install github.com/anthropics/skills/skill-creator --global

# Install skill for current project only
skillsmp install github.com/openclaw/openclaw --project
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `No API key configured` | Run `skillsmp config --set-key <key>` |
| `INVALID_API_KEY` | Regenerate at skillsmp.com |
| `DAILY_QUOTA_EXCEEDED` | Wait until midnight UTC |
| `Skill already exists` | Use prompt to update or manually delete |

## Related

- [SkillsMP Marketplace](https://skillsmp.com)
- [Official Anthropic Skills](https://github.com/anthropics/skills)
- [Agent Skills Specification](https://agentskills.io/)
