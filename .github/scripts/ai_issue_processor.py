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


def get_openai_model():
    """Get OpenAI model name with fallback to accessible models."""
    # Try user-specified model first
    user_model = os.getenv("OPENAI_MODEL")
    if user_model:
        return user_model
    
    # Default to more accessible models (in order of preference)
    # gpt-4-turbo is more accessible than gpt-4
    # gpt-3.5-turbo is the most accessible
    return "gpt-5-mini"


def get_anthropic_model():
    """Get Anthropic model name with fallback."""
    user_model = os.getenv("ANTHROPIC_MODEL")
    if user_model:
        return user_model
    return "claude-3-5-sonnet-20241022"


def parse_json_response(content: str) -> Dict[str, Any]:
    """
    Parse JSON from AI response, handling markdown code blocks and malformed JSON.
    
    Args:
        content: Raw content from AI response
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
    """
    if not content:
        raise json.JSONDecodeError("Empty content", content, 0)
    
    # Remove markdown code blocks if present
    content = content.strip()
    
    # Try to extract JSON from markdown code blocks
    if content.startswith("```"):
        # Find the first ``` and extract content between ``` and ```
        lines = content.split("\n")
        json_lines = []
        in_code_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_code_block:
                    # Starting code block, skip language identifier
                    in_code_block = True
                    continue
                else:
                    # Ending code block
                    break
            if in_code_block:
                json_lines.append(line)
        if json_lines:
            content = "\n".join(json_lines).strip()
        else:
            # Try to extract JSON after the first ```
            parts = content.split("```", 2)
            if len(parts) >= 2:
                potential_json = parts[1].strip()
                # Remove language identifier if present (e.g., json)
                if potential_json.startswith("json"):
                    potential_json = potential_json[4:].strip()
                # Remove trailing ``` if present
                if potential_json.endswith("```"):
                    potential_json = potential_json[:-3].strip()
                content = potential_json
    
    # Try to find JSON object boundaries if content is malformed
    # Look for first { and last }
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        content = content[first_brace:last_brace + 1]
    
    # Try parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Log the problematic content for debugging
        print(f"JSON parsing error at position {e.pos}: {e.msg}")
        error_start = max(0, e.pos - 200)
        error_end = min(len(content), e.pos + 200)
        print(f"Content around error (chars {error_start}-{error_end}):")
        print(content[error_start:error_end])
        print(f"\nFull content length: {len(content)}")
        # Try to provide more context
        if e.pos < len(content):
            print(f"Character at error position: {repr(content[e.pos])}")
        raise


def get_repo_context() -> str:
    """Get repository context by reading key files."""
    context_parts = []
    
    # Read project structure
    repo_root = Path(".")
    
    # Read AGENTS.md for project guidelines
    if (repo_root / "AGENTS.md").exists():
        with open(repo_root / "AGENTS.md", "r", encoding="utf-8") as f:
            context_parts.append(f"## Project Guidelines\n{f.read()}\n")
    
    # Read README files (limit size to avoid rate limits)
    for readme in ["README.md", "backend/README.md", "frontend/README.md"]:
        if (repo_root / readme).exists():
            with open(repo_root / readme, "r", encoding="utf-8") as f:
                content = f.read()[:1500]  # Limit to 1500 chars per README
                context_parts.append(f"## {readme}\n{content}\n")
    
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

    # Try models in order of preference with fallback
    openai_models = ["gpt-5-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    
    try:
        if isinstance(client, openai.OpenAI):
            model = get_openai_model()
            # If user specified a model, try it first, then fallback
            if model not in openai_models:
                models_to_try = [model] + openai_models
            else:
                models_to_try = openai_models
            
            last_error = None
            for model_to_try in models_to_try:
                try:
                    print(f"Trying OpenAI model: {model_to_try}")
                    response = client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {"role": "system", "content": "You are an expert software developer. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        response_format={"type": "json_object"}
                    )
                    raw_content = response.choices[0].message.content
                    result = parse_json_response(raw_content)
                    print(f"Successfully used model: {model_to_try}")
                    return result
                except Exception as model_error:
                    last_error = model_error
                    if "model_not_found" in str(model_error) or "does not exist" in str(model_error):
                        print(f"Model {model_to_try} not available, trying next...")
                        continue
                    else:
                        # Other error, don't try other models
                        raise
            
            # If we get here, all models failed
            raise last_error if last_error else Exception("All models failed")
        
        elif isinstance(client, anthropic.Anthropic):
            model = get_anthropic_model()
            # If user specified a model, try it first, then fallback
            if model not in anthropic_models:
                models_to_try = [model] + anthropic_models
            else:
                models_to_try = anthropic_models
            
            last_error = None
            for model_to_try in models_to_try:
                try:
                    print(f"Trying Anthropic model: {model_to_try}")
                    response = client.messages.create(
                        model=model_to_try,
                        max_tokens=2000,
                        system="You are an expert software developer. Always respond with valid JSON.",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw_content = response.content[0].text
                    result = parse_json_response(raw_content)
                    print(f"Successfully used model: {model_to_try}")
                    return result
                except Exception as model_error:
                    last_error = model_error
                    if "model_not_found" in str(model_error) or "does not exist" in str(model_error):
                        print(f"Model {model_to_try} not available, trying next...")
                        continue
                    else:
                        # Other error, don't try other models
                        raise
            
            # If we get here, all models failed
            raise last_error if last_error else Exception("All models failed")
    
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
    
    # Read existing files (limit size to avoid rate limits)
    file_contents = {}
    max_file_size = 50000  # Limit each file to ~50KB to avoid token limits
    for file_path in files_to_modify:
        path = Path(file_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Truncate if too large
                    if len(content) > max_file_size:
                        print(f"Warning: {file_path} is large ({len(content)} chars), truncating to {max_file_size} chars")
                        content = content[:max_file_size] + "\n# ... (file truncated due to size limits) ..."
                    file_contents[file_path] = content
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

    # Try models in order of preference with fallback
    openai_models = ["gpt-5-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
    
    result = None
    
    try:
        if isinstance(client, openai.OpenAI):
            model = get_openai_model()
            # If user specified a model, try it first, then fallback
            if model not in openai_models:
                models_to_try = [model] + openai_models
            else:
                models_to_try = openai_models
            
            last_error = None
            for model_to_try in models_to_try:
                try:
                    print(f"Trying OpenAI model: {model_to_try}")
                    response = client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {"role": "system", "content": "You are an expert software developer. Always respond with valid JSON. Provide complete file contents, not diffs. Ensure all strings are properly escaped for JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        response_format={"type": "json_object"}
                    )
                    raw_content = response.choices[0].message.content
                    try:
                        result = parse_json_response(raw_content)
                        print(f"Successfully used model: {model_to_try}")
                        break
                    except json.JSONDecodeError as json_error:
                        # If JSON parsing fails, try to ask the AI to fix it
                        print(f"JSON parsing failed, attempting to fix: {json_error}")
                        try:
                            fix_response = client.chat.completions.create(
                                model=model_to_try,
                                messages=[
                                    {"role": "system", "content": "You are a JSON validator. Fix the JSON and return ONLY valid JSON, no explanations."},
                                    {"role": "user", "content": f"Fix this JSON:\n\n{raw_content}"}
                                ],
                                temperature=0.1,
                                response_format={"type": "json_object"}
                            )
                            fixed_content = fix_response.choices[0].message.content
                            result = parse_json_response(fixed_content)
                            print(f"Successfully fixed and parsed JSON with model: {model_to_try}")
                            break
                        except Exception as fix_error:
                            print(f"Failed to fix JSON: {fix_error}")
                            error_str = str(fix_error)
                            # If it's a rate limit error, fail immediately
                            if "rate_limit" in error_str.lower() or "429" in error_str or "tokens per min" in error_str.lower():
                                raise Exception(f"Rate limit exceeded while fixing JSON: {error_str}") from fix_error
                            # Continue to next model for other errors
                            last_error = json_error
                            continue
                except Exception as model_error:
                    last_error = model_error
                    error_str = str(model_error)
                    if "model_not_found" in error_str or "does not exist" in error_str:
                        print(f"Model {model_to_try} not available, trying next...")
                        continue
                    elif "rate_limit" in error_str.lower() or "429" in error_str or "tokens per min" in error_str.lower():
                        print(f"Rate limit error with {model_to_try}: {error_str}")
                        # Rate limit errors should fail immediately, don't try other models
                        raise Exception(f"Rate limit exceeded: {error_str}") from model_error
                    else:
                        # Other error, don't try other models
                        raise
            
            if result is None:
                error_msg = "All OpenAI models failed"
                if last_error:
                    error_msg = f"{error_msg}: {str(last_error)}"
                raise Exception(error_msg) from last_error
        
        elif isinstance(client, anthropic.Anthropic):
            model = get_anthropic_model()
            # If user specified a model, try it first, then fallback
            if model not in anthropic_models:
                models_to_try = [model] + anthropic_models
            else:
                models_to_try = anthropic_models
            
            last_error = None
            for model_to_try in models_to_try:
                try:
                    print(f"Trying Anthropic model: {model_to_try}")
                    response = client.messages.create(
                        model=model_to_try,
                        max_tokens=8000,
                        system="You are an expert software developer. Always respond with valid JSON. Provide complete file contents, not diffs. Ensure all strings are properly escaped for JSON.",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw_content = response.content[0].text
                    try:
                        result = parse_json_response(raw_content)
                        print(f"Successfully used model: {model_to_try}")
                        break
                    except json.JSONDecodeError as json_error:
                        # If JSON parsing fails, try to ask the AI to fix it
                        print(f"JSON parsing failed, attempting to fix: {json_error}")
                        try:
                            fix_response = client.messages.create(
                                model=model_to_try,
                                max_tokens=8000,
                                system="You are a JSON validator. Fix the JSON and return ONLY valid JSON, no explanations.",
                                messages=[{"role": "user", "content": f"Fix this JSON:\n\n{raw_content}"}]
                            )
                            fixed_content = fix_response.content[0].text
                            result = parse_json_response(fixed_content)
                            print(f"Successfully fixed and parsed JSON with model: {model_to_try}")
                            break
                        except Exception as fix_error:
                            print(f"Failed to fix JSON: {fix_error}")
                            error_str = str(fix_error)
                            # If it's a rate limit error, fail immediately
                            if "rate_limit" in error_str.lower() or "429" in error_str or "tokens per min" in error_str.lower():
                                raise Exception(f"Rate limit exceeded while fixing JSON: {error_str}") from fix_error
                            # Continue to next model for other errors
                            last_error = json_error
                            continue
                except Exception as model_error:
                    last_error = model_error
                    error_str = str(model_error)
                    if "model_not_found" in error_str or "does not exist" in error_str:
                        print(f"Model {model_to_try} not available, trying next...")
                        continue
                    elif "rate_limit" in error_str.lower() or "429" in error_str or "tokens per min" in error_str.lower():
                        print(f"Rate limit error with {model_to_try}: {error_str}")
                        # Rate limit errors should fail immediately, don't try other models
                        raise Exception(f"Rate limit exceeded: {error_str}") from model_error
                    else:
                        # Other error, don't try other models
                        raise
            
            if result is None:
                error_msg = "All Anthropic models failed"
                if last_error:
                    error_msg = f"{error_msg}: {str(last_error)}"
                raise Exception(error_msg) from last_error
        else:
            return False
        
        if result is None:
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
    try:
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
    except Exception as e:
        print(f"ERROR: Failed to implement changes: {e}")
        import traceback
        traceback.print_exc()
        # Set output and exit with error code
        with open(os.getenv("GITHUB_OUTPUT", "/dev/stdout"), "a") as f:
            f.write("has_changes=false\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
