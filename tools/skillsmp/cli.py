#!/usr/bin/env python3
"""
SkillsMP CLI - Search and install agent skills from skillsmp.com

Usage:
    skillsmp search <query> [--limit N] [--sort stars|recent]
    skillsmp ai-search <query>
    skillsmp install <skill-url> [--global|--project]
    skillsmp config --set-key <api_key>
    skillsmp quota

Examples:
    skillsmp search "code review" --limit 10 --sort stars
    skillsmp ai-search "how to automate PR reviews"
    skillsmp install https://github.com/user/repo --global
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Config paths
CONFIG_DIR = Path.home() / ".skillsmp"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
GLOBAL_SKILLS_DIR = Path.home() / ".claude" / "skills"
PROJECT_SKILLS_DIR = Path(".claude") / "skills"

# API
API_BASE = "https://skillsmp.com/api/v1/skills"


def get_api_key() -> Optional[str]:
    """Get API key from env var or config file."""
    # Try environment variable first
    key = os.environ.get("SKILLSMP_API_KEY")
    if key:
        return key
    
    # Try config file
    if CONFIG_FILE.exists():
        try:
            import yaml
            with open(CONFIG_FILE) as f:
                config = yaml.safe_load(f)
                return config.get("api_key")
        except ImportError:
            # Fallback: simple YAML parsing for api_key line
            with open(CONFIG_FILE) as f:
                for line in f:
                    if line.strip().startswith("api_key:"):
                        return line.split(":", 1)[1].strip().strip('"\'')
    return None


def set_api_key(key: str) -> None:
    """Save API key to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(f"api_key: {key}\n")
    print(f"API key saved to {CONFIG_FILE}")


def api_request(endpoint: str, params: dict = None) -> dict:
    """Make authenticated API request."""
    api_key = get_api_key()
    if not api_key:
        print("Error: No API key configured.")
        print("Set with: skillsmp config --set-key <your_key>")
        print("Or: export SKILLSMP_API_KEY=<your_key>")
        print("\nGet your key at: https://skillsmp.com/auth/login")
        sys.exit(1)
    
    url = f"{API_BASE}/{endpoint}"
    if params:
        url = f"{url}?{urlencode(params)}"
    
    req = Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        with urlopen(req, timeout=30) as resp:
            # Show rate limit info from headers
            remaining = resp.headers.get("X-RateLimit-Daily-Remaining", "?")
            limit = resp.headers.get("X-RateLimit-Daily-Limit", "500")
            print(f"[Quota: {remaining}/{limit} requests remaining]", file=sys.stderr)
            
            return json.loads(resp.read().decode())
    except HTTPError as e:
        body = e.read().decode()
        try:
            error = json.loads(body)
            print(f"API Error: {error.get('error', {}).get('message', body)}")
        except json.JSONDecodeError:
            print(f"HTTP {e.code}: {body}")
        sys.exit(1)
    except URLError as e:
        print(f"Network error: {e.reason}")
        sys.exit(1)


def search(query: str, limit: int = 20, sort_by: str = "stars") -> None:
    """Keyword search for skills."""
    print(f"Searching for: {query}")
    print("-" * 50)
    
    result = api_request("search", {
        "q": query,
        "limit": limit,
        "sortBy": sort_by
    })
    
    # API returns: { "success": true, "data": { "skills": [...] } }
    data = result.get("data", {})
    skills = data.get("skills", []) if isinstance(data, dict) else []
    
    if not skills:
        print("No skills found.")
        return
    
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(skills))
    print(f"Found {total} skills (showing {len(skills)})\n")
    
    for i, skill in enumerate(skills, 1):
        name = skill.get("name", "Unknown")
        author = skill.get("author", "")
        desc = skill.get("description", "")[:80]
        stars = skill.get("stars", 0)
        github_url = skill.get("githubUrl", "")
        
        print(f"{i}. {name} by {author} ★{stars}")
        print(f"   {desc}")
        print(f"   {github_url}")
        print()


def ai_search(query: str) -> None:
    """AI semantic search for skills."""
    print(f"AI Search: {query}")
    print("-" * 50)
    
    result = api_request("ai-search", {"q": query})
    
    # API returns: { "success": true, "data": { "skills": [...] } }
    data = result.get("data", {})
    skills = data.get("skills", []) if isinstance(data, dict) else []
    
    if not skills:
        print("No skills found.")
        return
    
    print(f"Found {len(skills)} relevant skills\n")
    
    for i, skill in enumerate(skills, 1):
        name = skill.get("name", "Unknown")
        author = skill.get("author", "")
        desc = skill.get("description", "")[:80]
        stars = skill.get("stars", 0)
        github_url = skill.get("githubUrl", "")
        score = skill.get("score", skill.get("similarity", ""))
        
        print(f"{i}. {name} by {author} ★{stars}")
        if score:
            print(f"   Relevance: {score}")
        print(f"   {desc}")
        print(f"   {github_url}")
        print()


def find_skill_directories(repo_dir: Path) -> list:
    """Find all directories containing SKILL.md files."""
    skill_files = list(repo_dir.rglob("SKILL.md"))
    # Return parent directories (the skill folder)
    return [f.parent for f in skill_files]


def extract_skills(repo_dir: Path, base_install_dir: Path, interactive: bool = True) -> int:
    """Extract individual skills from a repo with nested structure.
    
    Returns number of skills extracted.
    """
    skill_dirs = find_skill_directories(repo_dir)
    
    if not skill_dirs:
        print("No SKILL.md files found in repository.")
        return 0
    
    # Check if it's a single skill at root
    if len(skill_dirs) == 1 and skill_dirs[0] == repo_dir:
        print("Single skill at repo root - already installed correctly.")
        return 1
    
    print(f"\nFound {len(skill_dirs)} skills in nested structure:")
    for i, skill_dir in enumerate(skill_dirs[:20], 1):
        rel_path = skill_dir.relative_to(repo_dir)
        skill_name = skill_dir.name
        print(f"  {i}. {skill_name} ({rel_path})")
    
    if len(skill_dirs) > 20:
        print(f"  ... and {len(skill_dirs) - 20} more")
    
    if interactive:
        print("\nOptions:")
        print("  a = Extract ALL skills to ~/.claude/skills/")
        print("  1,2,5 = Extract specific skills by number")
        print("  n = Skip extraction (keep nested structure)")
        response = input("\nExtract skills? [a/numbers/n]: ").strip().lower()
        
        if response == "n" or response == "":
            print("Keeping nested structure.")
            return 0
        elif response == "a":
            indices = list(range(len(skill_dirs)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in response.split(",")]
                indices = [i for i in indices if 0 <= i < len(skill_dirs)]
            except ValueError:
                print("Invalid input. Keeping nested structure.")
                return 0
    else:
        # Non-interactive: extract all
        indices = list(range(len(skill_dirs)))
    
    extracted = 0
    for idx in indices:
        skill_dir = skill_dirs[idx]
        skill_name = skill_dir.name
        target = base_install_dir / skill_name
        
        if target.exists():
            print(f"  Skipping {skill_name} (already exists)")
            continue
        
        # Copy skill directory
        import shutil
        shutil.copytree(skill_dir, target)
        print(f"  Extracted: {skill_name}")
        extracted += 1
    
    return extracted


def install(url: str, global_install: bool = True, extract: bool = True) -> None:
    """Install a skill from GitHub URL."""
    # Extract repo info from URL
    # Supports: https://github.com/user/repo or github.com/user/repo
    # Also supports: https://github.com/user/repo/tree/main/path/to/skill
    url = url.replace("https://", "").replace("http://", "")
    if url.startswith("github.com/"):
        url = url[11:]
    
    parts = url.strip("/").split("/")
    if len(parts) < 2:
        print(f"Invalid GitHub URL: {url}")
        print("Expected format: github.com/user/repo or https://github.com/user/repo")
        sys.exit(1)
    
    user, repo = parts[0], parts[1]
    
    # Check if URL points to a specific path (tree/branch/path)
    subpath = None
    if len(parts) > 4 and parts[2] == "tree":
        # github.com/user/repo/tree/branch/path/to/skill
        subpath = "/".join(parts[4:])
    
    github_url = f"https://github.com/{user}/{repo}"
    
    # Determine install location
    if global_install:
        base_install_dir = GLOBAL_SKILLS_DIR
        if subpath:
            # Installing specific skill from path
            skill_name = parts[-1]  # Last component of path
            target_dir = base_install_dir / skill_name
        else:
            target_dir = base_install_dir / repo
    else:
        # Find project root (look for .claude, .git, or use cwd)
        project_root = Path.cwd()
        for parent in [Path.cwd()] + list(Path.cwd().parents):
            if (parent / ".git").exists() or (parent / ".claude").exists():
                project_root = parent
                break
        base_install_dir = project_root / ".claude" / "skills"
        if subpath:
            skill_name = parts[-1]
            target_dir = base_install_dir / skill_name
        else:
            target_dir = base_install_dir / repo
    
    # For specific subpath, use sparse checkout
    if subpath:
        if target_dir.exists():
            print(f"Skill already exists at: {target_dir}")
            return
        
        print(f"Installing skill from {github_url} (path: {subpath})...")
        
        # Clone with sparse checkout for specific path
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / repo
            try:
                # Clone sparse
                subprocess.run([
                    "git", "clone", "--depth", "1", "--filter=blob:none",
                    "--sparse", github_url, str(tmp_path)
                ], check=True, capture_output=True)
                
                subprocess.run([
                    "git", "-C", str(tmp_path), "sparse-checkout", "set", subpath
                ], check=True, capture_output=True)
                
                # Copy the skill folder
                import shutil
                source = tmp_path / subpath
                if source.exists():
                    target_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(source, target_dir)
                    print(f"Installed to: {target_dir}")
                    
                    if (target_dir / "SKILL.md").exists():
                        print("SKILL.md found!")
                    else:
                        print("Warning: No SKILL.md in extracted path")
                else:
                    print(f"Path not found: {subpath}")
                    sys.exit(1)
                    
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone: {e}")
                sys.exit(1)
        return
    
    # Full repo clone
    if target_dir.exists():
        print(f"Repo already exists at: {target_dir}")
        response = input("Update? [y/N]: ").strip().lower()
        if response == "y":
            print(f"Updating {repo}...")
            subprocess.run(["git", "-C", str(target_dir), "pull"], check=True)
            
            if extract:
                # Re-check for nested skills after update
                skill_dirs = find_skill_directories(target_dir)
                if len(skill_dirs) > 1 or (len(skill_dirs) == 1 and skill_dirs[0] != target_dir):
                    extract_skills(target_dir, base_install_dir)
            print("Done!")
        return
    
    # Clone the repo
    print(f"Installing {repo} from {github_url}...")
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", github_url, str(target_dir)],
            check=True
        )
        print(f"Cloned to: {target_dir}")
        
        # Check for SKILL.md at root
        skill_md = target_dir / "SKILL.md"
        if skill_md.exists():
            print("SKILL.md found at root - ready to use!")
            return
        
        # Look for nested skills
        skill_dirs = find_skill_directories(target_dir)
        
        if not skill_dirs:
            print("Warning: No SKILL.md found in repository")
            return
        
        if extract and len(skill_dirs) >= 1:
            print(f"\nRepo contains {len(skill_dirs)} nested skill(s).")
            extracted = extract_skills(target_dir, base_install_dir)
            
            if extracted > 0:
                print(f"\nExtracted {extracted} skill(s) to {base_install_dir}")
                print("Tip: You can remove the cloned repo if not needed:")
                print(f"  rm -rf {target_dir}")
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone: {e}")
        sys.exit(1)


def list_installed(location: str = "all") -> None:
    """List installed skills."""
    locations = []
    
    if location in ("all", "global"):
        locations.append(("Global", GLOBAL_SKILLS_DIR))
    if location in ("all", "project"):
        # Find project root
        project_root = Path.cwd()
        for parent in [Path.cwd()] + list(Path.cwd().parents):
            if (parent / ".git").exists() or (parent / ".claude").exists():
                project_root = parent
                break
        project_skills = project_root / ".claude" / "skills"
        if project_skills.exists():
            locations.append(("Project", project_skills))
    
    total = 0
    for name, path in locations:
        if not path.exists():
            continue
        
        print(f"\n{name} skills ({path}):")
        print("-" * 50)
        
        # Find all SKILL.md files
        skills = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    skills.append((item.name, "ready"))
                else:
                    # Check for nested skills
                    nested = list(item.rglob("SKILL.md"))
                    if nested:
                        skills.append((item.name, f"nested ({len(nested)} skills)"))
                    else:
                        skills.append((item.name, "no SKILL.md"))
        
        if not skills:
            print("  (none)")
            continue
        
        for skill_name, status in skills:
            if status == "ready":
                print(f"  ✓ {skill_name}")
            elif "nested" in status:
                print(f"  ◐ {skill_name} [{status}]")
            else:
                print(f"  ✗ {skill_name} [{status}]")
            total += 1
    
    print(f"\nTotal: {total} skill directories")


def flatten(repo_name: str = None) -> None:
    """Extract nested skills from an already-cloned repository."""
    if repo_name:
        target = GLOBAL_SKILLS_DIR / repo_name
        if not target.exists():
            print(f"Repository not found: {target}")
            sys.exit(1)
        repos = [target]
    else:
        # Find all repos with nested skills
        repos = []
        if GLOBAL_SKILLS_DIR.exists():
            for item in GLOBAL_SKILLS_DIR.iterdir():
                if item.is_dir():
                    nested = list(item.rglob("SKILL.md"))
                    # Has nested skills but no root SKILL.md
                    if nested and not (item / "SKILL.md").exists():
                        repos.append(item)
        
        if not repos:
            print("No repositories with nested skills found.")
            return
        
        print(f"Found {len(repos)} repo(s) with nested skills:")
        for repo in repos:
            nested_count = len(list(repo.rglob("SKILL.md")))
            print(f"  - {repo.name} ({nested_count} skills)")
    
    for repo in repos:
        print(f"\nExtracting from {repo.name}...")
        extract_skills(repo, GLOBAL_SKILLS_DIR)


def show_quota() -> None:
    """Show remaining API quota."""
    api_key = get_api_key()
    if not api_key:
        print("No API key configured.")
        return
    
    # Make a minimal request just to get quota headers
    print("Checking quota...")
    api_request("search", {"q": "test", "limit": 1})


def main():
    parser = argparse.ArgumentParser(
        description="Search and install agent skills from skillsmp.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Keyword search for skills")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=20, help="Max results (default: 20)")
    search_parser.add_argument("--sort", "-s", choices=["stars", "recent"], default="stars", help="Sort by")
    
    # ai-search command
    ai_parser = subparsers.add_parser("ai-search", help="AI semantic search")
    ai_parser.add_argument("query", help="Natural language query")
    
    # install command
    install_parser = subparsers.add_parser("install", help="Install skill from GitHub")
    install_parser.add_argument("url", help="GitHub repository URL (supports full paths like github.com/user/repo/tree/main/path/to/skill)")
    install_parser.add_argument("--global", "-g", dest="global_install", action="store_true", default=True, help="Install globally (default)")
    install_parser.add_argument("--project", "-p", dest="global_install", action="store_false", help="Install to current project")
    install_parser.add_argument("--no-extract", dest="extract", action="store_false", default=True, help="Don't extract nested skills")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List installed skills")
    list_parser.add_argument("--global", "-g", dest="location", action="store_const", const="global", default="all", help="Show only global skills")
    list_parser.add_argument("--project", "-p", dest="location", action="store_const", const="project", help="Show only project skills")
    
    # flatten command
    flatten_parser = subparsers.add_parser("flatten", help="Extract nested skills from cloned repos")
    flatten_parser.add_argument("repo", nargs="?", help="Specific repo name (default: all with nested skills)")
    
    # config command
    config_parser = subparsers.add_parser("config", help="Configure CLI")
    config_parser.add_argument("--set-key", dest="api_key", help="Set API key")
    
    # quota command
    subparsers.add_parser("quota", help="Show remaining API quota")
    
    args = parser.parse_args()
    
    if args.command == "search":
        search(args.query, args.limit, args.sort)
    elif args.command == "ai-search":
        ai_search(args.query)
    elif args.command == "install":
        install(args.url, args.global_install, args.extract)
    elif args.command == "list":
        list_installed(args.location)
    elif args.command == "flatten":
        flatten(args.repo)
    elif args.command == "config":
        if args.api_key:
            set_api_key(args.api_key)
        else:
            print("Current config:")
            key = get_api_key()
            if key:
                print(f"  API key: {key[:10]}...{key[-4:]}")
            else:
                print("  No API key set")
    elif args.command == "quota":
        show_quota()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
