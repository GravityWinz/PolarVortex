#!/usr/bin/env python3
"""
AI Issue Processor

This script processes GitHub issues using AI to generate code changes.
It reads the issue details, analyzes the requirements, and makes appropriate changes.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import AI libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def get_ai_client():
    """Initialize and return an AI client based on available API keys."""
    if os.getenv("OPENAI_API_KEY"):
        if not OPENAI_AVAILABLE:
            print("Warning: OpenAI API key found but openai package not installed")
            return None
        return openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    if os.getenv("ANTHROPIC_API_KEY"):
        if not ANTHROPIC_AVAILABLE:
            print("Warning: Anthropic API key found but anthropic package not installed")
            return None
        return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    print("Warning: No AI API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    return None


def get_repo_context() -> str:
    """Get repository context by reading key files."""
    context_parts = []
    
    # Read project structure
    repo_root = Path(".")
    
    # Read AGENTS.md for project guidelines
    if (repo_root / "AGENTS.md").exists():
        with open(repo_root / "AGENTS.md", "r", encoding="utf-8") as f:
            context_parts.append(f"## Project Guidelines\n{f.read()}\n")
    
    # Read README files
    for readme in ["README.md", "backend/README.md", "frontend/README.md"]:
        if (repo_root / readme).exists():
            with open(repo_root / readme, "r", encoding="utf-8") as f:
                context_parts.append(f"## {readme}\n{f.read()[:2000]}\n")  # Limit size
    
    # Get file structure
    try:
        result = subprocess.run(
            ["find", ".", "-type", "f", "-name", "*.py", "-o", "-name", "*.jsx", "-o", "-name", "*.tsx"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            files = result.stdout.strip().split("\n")[:50]  # Limit to 50 files
            context_parts.append(f"## Key Files\n{chr(10).join(files)}\n")
    except:
        pass
    
    return "\n".join(context_parts)


def analyze_issue_with_ai(client: Any, issue_title: str, issue_body: str, repo_context: str) -> Dict[str, Any]:
    """Use AI to analyze the issue and generate a plan."""
    
    prompt = f"""You are an expert software developer working on the PolarVortex project, a polargraph plotter control system.

## Project Context
{repo_context}

## Issue to Address
**Title:** {issue_title}

**Description:**
{issue_body}

## Your Task
Analyze this issue and provide:
1. A clear understanding of what needs to be done
2. A list of files that likely need to be modified
3. A step-by-step plan for implementation
4. Any potential challenges or considerations

Respond in JSON format:
{{
  "understanding": "Brief summary of what needs to be done",
  "files_to_modify": ["path/to/file1.py", "path/to/file2.jsx"],
  "implementation_plan": ["Step 1", "Step 2", "Step 3"],
  "challenges": ["Challenge 1", "Challenge 2"],
  "can_implement": true/false
}}
"""

    try:
        if isinstance(client, openai.OpenAI):
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are an expert software developer. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result
        
        elif isinstance(client, anthropic.Anthropic):
            response = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                max_tokens=2000,
                system="You are an expert software developer. Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}]
            )
            result = json.loads(response.content[0].text)
            return result
    
    except Exception as e:
        print(f"Error calling AI API: {e}")
        return {"can_implement": False, "error": str(e)}
    
    return {"can_implement": False, "error": "Unknown AI client type"}


def implement_changes_with_ai(client: Any, analysis: Dict[str, Any], issue_title: str, issue_body: str, repo_context: str) -> bool:
    """Use AI to implement the changes based on the analysis."""
    
    files_to_modify = analysis.get("files_to_modify", [])
    if not files_to_modify:
        print("No files identified for modification")
        return False
    
    # Read existing files
    file_contents = {}
    for file_path in files_to_modify:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_contents[file_path] = f.read()
            except Exception as e:
                print(f"Warning: Could not read {file_path}: {e}")
    
    prompt = f"""You are an expert software developer working on the PolarVortex project.

## Project Context
{repo_context}

## Issue to Address
**Title:** {issue_title}
**Description:** {issue_body}

## Analysis
{json.dumps(analysis, indent=2)}

## Current Files
{json.dumps(file_contents, indent=2)}

## Your Task
Implement the changes needed to address this issue. For each file that needs modification, provide the complete updated file content.

Respond in JSON format:
{{
  "files": {{
    "path/to/file1.py": "complete file content here",
    "path/to/file2.jsx": "complete file content here"
  }},
  "summary": "Brief summary of changes made",
  "notes": "Any important notes about the implementation"
}}
"""

    try:
        if isinstance(client, openai.OpenAI):
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                messages=[
                    {"role": "system", "content": "You are an expert software developer. Always respond with valid JSON. Provide complete file contents, not diffs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
        
        elif isinstance(client, anthropic.Anthropic):
            response = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                max_tokens=8000,
                system="You are an expert software developer. Always respond with valid JSON. Provide complete file contents, not diffs.",
                messages=[{"role": "user", "content": prompt}]
            )
            result = json.loads(response.content[0].text)
        else:
            return False
        
        # Write files
        files_written = 0
        for file_path, content in result.get("files", {}).items():
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            files_written += 1
            print(f"Updated: {file_path}")
        
        if files_written > 0:
            print(f"\nSummary: {result.get('summary', 'Changes implemented')}")
            if result.get("notes"):
                print(f"Notes: {result.get('notes')}")
            return True
        
    except Exception as e:
        print(f"Error implementing changes: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False


def main():
    """Main entry point for the AI issue processor."""
    issue_number = os.getenv("ISSUE_NUMBER")
    issue_title = os.getenv("ISSUE_TITLE", "")
    issue_body = os.getenv("ISSUE_BODY", "")
    
    if not issue_number:
        print("Error: ISSUE_NUMBER environment variable not set")
        sys.exit(1)
    
    print(f"Processing issue #{issue_number}: {issue_title}")
    
    # Get AI client
    client = get_ai_client()
    if not client:
        print("No AI client available. Exiting.")
        sys.exit(0)
    
    # Get repository context
    print("Gathering repository context...")
    repo_context = get_repo_context()
    
    # Analyze issue
    print("Analyzing issue with AI...")
    analysis = analyze_issue_with_ai(client, issue_title, issue_body, repo_context)
    
    if not analysis.get("can_implement", False):
        print(f"Issue cannot be automatically implemented: {analysis.get('error', 'Unknown reason')}")
        print(f"Understanding: {analysis.get('understanding', 'N/A')}")
        sys.exit(0)
    
    print(f"Analysis complete. Files to modify: {analysis.get('files_to_modify', [])}")
    
    # Implement changes
    print("Implementing changes with AI...")
    success = implement_changes_with_ai(client, analysis, issue_title, issue_body, repo_context)
    
    if success:
        print("Changes implemented successfully")
        # Set output for GitHub Actions
        with open(os.getenv("GITHUB_OUTPUT", "/dev/stdout"), "a") as f:
            f.write("has_changes=true\n")
        sys.exit(0)
    else:
        print("No changes were made")
        with open(os.getenv("GITHUB_OUTPUT", "/dev/stdout"), "a") as f:
            f.write("has_changes=false\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
