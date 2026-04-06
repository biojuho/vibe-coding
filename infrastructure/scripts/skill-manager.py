import argparse
import os
import sys
from pathlib import Path


def create_skill(args):
    """Scaffolds a new skill structure."""
    name = args.name
    path = Path(args.path) / name

    if path.exists():
        print(f"Error: Directory '{path}' already exists.")
        sys.exit(1)

    os.makedirs(path)
    print(f"Creating skill '{name}' at {path}...")

    # Create required directories
    os.makedirs(path / "agents", exist_ok=True)

    # Create SKILL.md
    with open(path / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(f"""---
name: {name}
description: [Short description of what functionality this skill provides and when to use it]
---

# {name.replace("-", " ").title()}

## Overview
Describe the skill's purpose and core functionality.

## Usage
Provide instructions on how to use this skill.
""")

    # Create agents/openai.yaml
    with open(path / "agents" / "openai.yaml", "w", encoding="utf-8") as f:
        f.write(f"""name: {name}
display_name: {name.replace("-", " ").title()}
short_description: [Short description]
default_prompt: |
  You are an expert in {name}...
""")

    print(f"✅ Skill '{name}' created successfully!")


def validate_skill(args):
    """Validates the structure of a skill."""
    path = Path(args.path)

    if not path.exists():
        print(f"Error: Directory '{path}' does not exist.")
        sys.exit(1)

    print(f"Validating skill at {path}...")
    errors = []

    # Check SKILL.md
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing SKILL.md")
    else:
        # Check frontmatter
        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.startswith("---"):
                    errors.append("SKILL.md must start with YAML frontmatter (---)")
        except Exception as e:
            errors.append(f"Error reading SKILL.md: {e}")

    if errors:
        print("❌ Validation Failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("✅ Validation Command Passed! (Basic structure check)")


def main():
    parser = argparse.ArgumentParser(description="Vibe Coding Skill Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # New Skill Command
    new_parser = subparsers.add_parser("new", help="Create a new skill")
    new_parser.add_argument("name", help="Name of the skill")
    new_parser.add_argument("--path", default=".", help="Parent directory (e.g., .agents/skills)")
    new_parser.set_defaults(func=create_skill)

    # Validate Skill Command
    val_parser = subparsers.add_parser("validate", help="Validate a skill")
    val_parser.add_argument("path", help="Path to the skill directory")
    val_parser.set_defaults(func=validate_skill)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
