# GitHub AI Workflow Integration

This document explains how to set up and use the AI-powered GitHub issue workflow for PolarVortex.

## Overview

The workflow automates the following process:
1. **Issue Creation**: Create an issue in GitHub describing the work needed
2. **Issue Assignment**: Assign the issue to the AI bot (or add the `ai-assigned` label)
3. **AI Processing**: The workflow automatically:
   - Creates a feature branch from the issue
   - Analyzes the issue using AI
   - Implements code changes
   - Commits and pushes changes
   - Creates a Pull Request
   - Links the PR to the original issue

## Prerequisites

Before you begin, make sure you have:
- A GitHub account (free account works fine)
- Your PolarVortex code pushed to a GitHub repository
- An API key from either OpenAI or Anthropic (for AI processing)

**Important**: You do NOT need to create a GitHub App or bot account! The workflow can work with labels or manual triggers.

## Complete Setup Guide

### Step 1: Ensure Your Code is on GitHub

If you haven't pushed your code to GitHub yet:

1. **Create a GitHub Repository** (if you don't have one):
   - Go to [github.com](https://github.com) and sign in
   - Click the **+** icon in the top right → **New repository**
   - Name it (e.g., `PolarVortex`)
   - Choose **Public** or **Private**
   - **Do NOT** initialize with README, .gitignore, or license (if you already have code)
   - Click **Create repository**

2. **Push Your Code to GitHub**:
   ```bash
   # If you haven't initialized git yet
   git init
   git add .
   git commit -m "Initial commit"
   
   # Add your GitHub repository as remote
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   
   # Push to GitHub
   git branch -M main  # or 'dev' if that's your default branch
   git push -u origin main
   ```

3. **Push the Workflow Files**:
   Make sure the `.github/workflows/ai-issue-handler.yml` file is committed and pushed:
   ```bash
   git add .github/
   git commit -m "Add AI issue handler workflow"
   git push
   ```

### Step 2: Get AI API Keys

You'll need an API key from either OpenAI or Anthropic (or both):

#### Option A: Get OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to **API keys** section: https://platform.openai.com/api-keys
4. Click **Create new secret key**
5. Give it a name (e.g., "PolarVortex GitHub Actions")
6. **Copy the key immediately** - you won't be able to see it again!
7. Save it somewhere safe temporarily (you'll add it to GitHub in the next step)

#### Option B: Get Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to **API Keys** section
4. Click **Create Key**
5. Give it a name (e.g., "PolarVortex GitHub Actions")
6. **Copy the key immediately**
7. Save it somewhere safe temporarily

**Note**: You only need one API key, but you can add both if you want flexibility.

### Step 3: Add API Keys to GitHub Secrets

**IMPORTANT SECURITY NOTE**: Never commit API keys to your code! Always use GitHub Secrets.

1. **Navigate to Your Repository on GitHub**:
   - Go to your repository page (e.g., `https://github.com/YOUR_USERNAME/PolarVortex`)

2. **Open Settings**:
   - Click the **Settings** tab (at the top of the repository page)
   - If you don't see Settings, make sure you're the repository owner or have admin access

3. **Go to Secrets**:
   - In the left sidebar, find **Secrets and variables**
   - Click **Actions** (under Secrets and variables)

4. **Add OpenAI Secret** (if using OpenAI):
   - Click **New repository secret** button
   - **Name**: Enter exactly `OPENAI_API_KEY` (case-sensitive)
   - **Secret**: Paste your OpenAI API key
   - Click **Add secret**

5. **Add Anthropic Secret** (if using Anthropic):
   - Click **New repository secret** button again
   - **Name**: Enter exactly `ANTHROPIC_API_KEY` (case-sensitive)
   - **Secret**: Paste your Anthropic API key
   - Click **Add secret**

6. **Verify Secrets**:
   - You should now see both secrets listed (if you added both)
   - The values will be hidden (showing only `••••••••`)
   - You can update or delete them later if needed

### Step 4: Enable GitHub Actions (if needed)

1. **Check Actions are Enabled**:
   - Go to your repository
   - Click the **Actions** tab
   - If you see a message about enabling Actions, click **I understand my workflows, enable them**

2. **Verify Workflow File**:
   - In the Actions tab, you should see "AI Issue Handler" in the workflow list
   - If not, make sure `.github/workflows/ai-issue-handler.yml` is committed and pushed

### Step 5: Enable Workflow Permissions (Required!)

**This is critical** - Without this, the workflow cannot create pull requests:

1. **Go to Repository Settings**:
   - Click **Settings** tab in your repository
   - In the left sidebar, click **Actions** → **General**

2. **Enable Workflow Permissions**:
   - Scroll down to the **Workflow permissions** section
   - Select **Read and write permissions** (not "Read repository contents and packages permissions")
   - **IMPORTANT**: Check the box **Allow GitHub Actions to create and approve pull requests**
   - Click **Save** at the bottom of the page

3. **Verify**:
   - You should see a green checkmark or confirmation that settings were saved
   - The workflow will now be able to create pull requests automatically

**Why this is needed**: GitHub Actions needs explicit permission to create pull requests for security reasons. This setting allows the workflow to create PRs on your behalf.

### Step 6: Create the `ai-assigned` Label (Recommended - Easiest Method)

This is the easiest way to trigger the workflow without needing a bot:

1. **Go to Issues Tab**:
   - Click **Issues** in your repository

2. **Open Labels**:
   - Click **Labels** (on the right side, or in the Issues page)

3. **Create New Label**:
   - Click **New label** button
   - **Label name**: Enter `ai-assigned` (exactly, lowercase with hyphen)
   - **Description**: "Issue assigned to AI for automatic processing"
   - Choose a color (e.g., purple or blue)
   - Click **Create label**

Now you can simply add this label to any issue to trigger the AI workflow!

## Usage Methods (Choose One)

You have three ways to trigger the workflow. **Method 2 (Label) is recommended** as it's the simplest and doesn't require any bot setup.

### Method 1: Use Label (Recommended - No Bot Needed!)

This is the easiest method and requires no bot setup:

1. **Create an Issue**:
   - Go to your repository → **Issues** tab
   - Click **New issue**
   - Write a clear description of what you want the AI to do
   - Click **Submit new issue**

2. **Add the Label**:
   - On the issue page, look for the **Labels** section (right sidebar)
   - Click the gear icon or "Labels" button
   - Select `ai-assigned`
   - The workflow will automatically trigger!

3. **Monitor Progress**:
   - Go to **Actions** tab to see the workflow running
   - The AI will create a branch, make changes, and open a PR
   - Check the issue for comments and updates

### Method 2: Manual Trigger (For Testing)

Use this to manually trigger the workflow for any issue:

1. **Go to Actions Tab**:
   - Click **Actions** in your repository

2. **Select Workflow**:
   - Click **AI Issue Handler** in the left sidebar

3. **Run Workflow**:
   - Click **Run workflow** button (top right)
   - Select the branch (usually `main` or `dev`)
   - Enter the issue number (e.g., `1`, `2`, `3`)
   - Click **Run workflow**

4. **Monitor Progress**:
   - Watch the workflow run in real-time
   - Check the logs if anything fails

### Method 3: Assign to Bot (Advanced - Requires Bot Setup)

This method requires setting up a GitHub App or bot account. **Skip this if you're using Method 1 (Label)**.

If you want to use assignment instead of labels:

1. **Option A: Use GitHub Actions Bot** (Simpler):
   - When creating/editing an issue, in the **Assignees** section
   - Type `github-actions[bot]` and select it
   - The workflow will trigger automatically

2. **Option B: Create a Custom Bot** (More Complex):
   - Create a GitHub App: https://github.com/settings/apps/new
   - Or create a separate GitHub account to use as a bot
   - Install it on your repository
   - Assign issues to that bot account

## Testing Your Setup

After completing the setup, test that everything works:

1. **Create a Test Issue**:
   - Go to **Issues** → **New issue**
   - Title: "Test AI Workflow"
   - Description: "This is a test issue to verify the AI workflow is working."
   - Click **Submit new issue**
   - Note the issue number (e.g., #1)

2. **Trigger the Workflow**:
   - Add the `ai-assigned` label to the issue, OR
   - Go to **Actions** → **AI Issue Handler** → **Run workflow** → Enter issue number

3. **Check the Results**:
   - Go to **Actions** tab to see the workflow running
   - Wait for it to complete (usually 2-5 minutes)
   - Check if a new branch was created
   - Check if a Pull Request was opened
   - Review the changes in the PR

## Understanding the Workflow

The workflow automatically:
1. **Detects the Trigger**: Checks if issue has `ai-assigned` label or is assigned to bot
2. **Gets Issue Details**: Reads the issue title and description
3. **Creates Branch**: Creates `ai/issue-{number}-{title}` branch from your default branch
4. **Runs AI Analysis**: Uses AI to understand what needs to be done
5. **Implements Changes**: AI makes code changes based on the issue
6. **Commits Changes**: Commits the changes to the branch
7. **Creates PR**: Opens a Pull Request with the changes
8. **Updates Issue**: Adds comments and labels to track progress

## Default Branch Configuration

The workflow automatically detects your default branch (usually `main`, `master`, or `dev`). You don't need to change anything unless you have a non-standard setup.

If your default branch is different, the workflow will detect it automatically. No configuration needed!

## Workflow Steps

1. **Checkout**: Gets the latest code
2. **Get Issue Info**: Retrieves issue details from GitHub
3. **Check AI Assignment**: Verifies the issue should be handled by AI
4. **Create Feature Branch**: Creates a branch named `ai/issue-{number}-{sanitized-title}`
5. **Install Dependencies**: Sets up Python and required packages
6. **Process with AI**: Runs the AI processor script
7. **Commit Changes**: Commits any changes made by AI
8. **Create Pull Request**: Opens a PR with the changes
9. **Update Issue**: Adds comments and labels to track progress

## AI Processor Script

The `.github/scripts/ai_issue_processor.py` script:

- Reads project context (AGENTS.md, README files, file structure)
- Analyzes the issue using AI
- Determines which files need modification
- Generates implementation plan
- Implements code changes
- Returns status to the workflow

### Customization

You can customize the AI behavior by:

1. **Changing AI Model**: Set environment variables:
   - `OPENAI_MODEL`: e.g., `gpt-4`, `gpt-4-turbo`
   - `ANTHROPIC_MODEL`: e.g., `claude-3-5-sonnet-20241022`

2. **Modifying Prompts**: Edit the prompts in `ai_issue_processor.py` to change how the AI analyzes and implements issues

3. **Adding Context**: The script automatically reads:
   - `AGENTS.md` (project guidelines)
   - README files
   - File structure

   You can add more context by modifying `get_repo_context()` function

## Example Issue Format

For best results, structure your issues clearly:

```markdown
## Description
Add a new vectorization algorithm for edge detection.

## Requirements
- Create a new vectorizer class in `backend/app/vectorizers/`
- Follow the BaseVectorizer interface
- Add configuration options for threshold and sensitivity
- Register the vectorizer in `__init__.py`

## Acceptance Criteria
- [ ] New algorithm appears in the vectorizer list
- [ ] Can process test images successfully
- [ ] Configuration options work correctly
```

## Troubleshooting

### Workflow doesn't trigger

**Problem**: Nothing happens when you add the label or assign the issue.

**Solutions**:
1. **Check the label name**: Must be exactly `ai-assigned` (lowercase, with hyphen)
2. **Verify workflow file exists**: Check that `.github/workflows/ai-issue-handler.yml` is in your repository
3. **Check Actions are enabled**: Go to **Settings** → **Actions** → **General** → Make sure "Allow all actions" is selected
4. **Check workflow file syntax**: Go to **Actions** tab → Look for any errors in the workflow file
5. **Verify you pushed the workflow**: Make sure the workflow file is committed and pushed to GitHub

### Workflow fails with "API key not found"

**Problem**: Workflow runs but fails with authentication errors.

**Solutions**:
1. **Verify secrets are set**: Go to **Settings** → **Secrets and variables** → **Actions**
2. **Check secret names**: Must be exactly `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (case-sensitive)
3. **Verify API key is valid**: Test your API key on the provider's website
4. **Check for typos**: Make sure there are no extra spaces when copying the key

### AI doesn't make changes

**Problem**: Workflow runs successfully but no code changes are made.

**Solutions**:
1. **Check workflow logs**: Go to **Actions** → Click on the failed run → Check the "Process issue with AI" step logs
2. **Verify API keys work**: The AI might be failing silently - check the logs for error messages
3. **Issue might be unclear**: The AI may determine the issue needs manual intervention
4. **Check issue description**: Make sure the issue clearly describes what needs to be done
5. **Review AI analysis**: Check the workflow logs to see what the AI understood from the issue

### "Branch already exists" error

**Problem**: Workflow says branch already exists.

**Solutions**:
- This is actually fine! The workflow will checkout the existing branch and continue work
- Previous changes will be preserved
- If you want a fresh start, delete the old branch first

### PR not created / "GitHub Actions is not permitted to create pull requests"

**Problem**: Workflow completes but no Pull Request appears, or you see an error about permissions.

**Solutions**:
1. **Enable Workflow Permissions** (Most Common Fix):
   - Go to **Settings** → **Actions** → **General**
   - Scroll to **Workflow permissions** section
   - Select **Read and write permissions** (not just "Read repository contents")
   - **CRITICAL**: Check the box **Allow GitHub Actions to create and approve pull requests**
   - Click **Save**
   - Re-run the workflow

2. **Check workflow logs**: Look for errors in the "Create Pull Request" step
   - If you see a 403 error, it's definitely a permissions issue
   - The workflow will add a comment to the issue with instructions if this happens

3. **Verify branch was pushed**: Check that the branch exists in your repository
   - Go to your repository → **Code** → **Branches**
   - Look for branches starting with `ai/issue-`

4. **Check if PR already exists**: The workflow won't create a duplicate PR
   - Check the **Pull requests** tab to see if a PR was already created

5. **Manual PR creation** (if permissions can't be enabled):
   - If you can't enable the permission (e.g., organization policy), you can manually create a PR
   - The workflow will still create the branch and make changes
   - Just create a PR from the `ai/issue-{number}-{title}` branch to your default branch

### "Permission denied" errors

**Problem**: Workflow fails with permission errors.

**Solutions**:
1. **Check repository settings**: Go to **Settings** → **Actions** → **General**
2. **Enable workflow permissions**: Under "Workflow permissions", select "Read and write permissions"
3. **Enable PR creation**: Check "Allow GitHub Actions to create and approve pull requests"
4. **Save changes**: Click "Save" at the bottom of the page

### Workflow runs but takes too long

**Problem**: Workflow seems stuck or takes forever.

**Solutions**:
1. **This is normal**: AI processing can take 2-5 minutes depending on issue complexity
2. **Check the logs**: The workflow is likely still running - check the "Process issue with AI" step
3. **API rate limits**: Your AI provider might be rate-limiting - wait a bit and try again
4. **Large codebase**: If your repository is very large, context gathering takes longer

### Can't find the Actions tab

**Problem**: You don't see the Actions tab in your repository.

**Solutions**:
1. **Check repository type**: Actions are available on all GitHub repositories (free accounts included)
2. **Verify you're on the right page**: Make sure you're viewing the repository, not your profile
3. **Check permissions**: Make sure you have access to the repository
4. **Try refreshing**: Sometimes the UI needs a refresh

### API key was exposed in documentation

**Problem**: You accidentally committed an API key to the repository.

**Solutions**:
1. **Immediately revoke the key**: Go to your AI provider's website and revoke the exposed key
2. **Create a new key**: Generate a new API key
3. **Add to GitHub Secrets**: Add the new key as a GitHub Secret (never commit it!)
4. **Remove from history** (if needed): Use `git filter-branch` or contact GitHub support for help removing sensitive data from git history

## Limitations

- The AI works best with clear, well-defined issues
- Complex issues may require multiple iterations
- The AI may not handle issues requiring external dependencies or API integrations
- Always review AI-generated code before merging

## Best Practices

1. **Clear Issue Descriptions**: Provide detailed requirements and context
2. **Review AI Changes**: Always review PRs before merging
3. **Iterative Approach**: Break large issues into smaller, focused ones
4. **Test Changes**: Run tests on AI-generated code
5. **Provide Feedback**: Update issues with feedback to improve AI understanding

## Security Considerations

### Protecting Your API Keys

**CRITICAL**: Never commit API keys to your code or documentation!

- ✅ **DO**: Store API keys in GitHub Secrets (encrypted and secure)
- ❌ **DON'T**: Commit API keys to git
- ❌ **DON'T**: Share API keys in issues, PRs, or documentation
- ❌ **DON'T**: Hardcode API keys in workflow files

### If You Accidentally Exposed a Key

1. **Immediately revoke it** on the provider's website
2. **Create a new key**
3. **Update the GitHub Secret** with the new key
4. **Remove from git history** if it was committed (use `git filter-branch` or GitHub support)

### Other Security Notes

- API keys are stored as GitHub Secrets (encrypted at rest)
- Workflow runs in isolated GitHub Actions environment
- Code changes are reviewed through PR process (you can review before merging)
- Consider rate limits for AI API usage
- Monitor your API usage to detect unauthorized access

## Cost Considerations

### Understanding AI API Costs

AI API calls have associated costs that vary by provider and model:

**OpenAI Pricing** (approximate):
- GPT-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- GPT-4 Turbo: ~$0.01 per 1K input tokens, ~$0.03 per 1K output tokens
- GPT-3.5 Turbo: ~$0.0005 per 1K input tokens, ~$0.0015 per 1K output tokens

**Anthropic Pricing** (approximate):
- Claude 3.5 Sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- Claude 3 Opus: ~$0.015 per 1K input tokens, ~$0.075 per 1K output tokens

**Typical Workflow Cost**:
- Simple issue: $0.10 - $0.50
- Complex issue: $0.50 - $2.00
- Very complex issue: $2.00 - $5.00+

### Managing Costs

1. **Monitor Usage**: Check your AI provider's dashboard regularly
2. **Set Usage Alerts**: Most providers allow you to set spending limits
3. **Use Appropriate Models**: 
   - Simple tasks: Use cheaper models (GPT-3.5 Turbo, Claude 3 Haiku)
   - Complex tasks: Use more capable models (GPT-4, Claude 3.5 Sonnet)
4. **Optimize Issues**: Clear, focused issues require less AI processing
5. **Review Before Running**: Don't trigger the workflow for issues that clearly need manual work

### Setting Usage Limits

**OpenAI**:
- Go to [platform.openai.com/account/billing/limits](https://platform.openai.com/account/billing/limits)
- Set hard and soft limits
- Configure alerts

**Anthropic**:
- Go to [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing)
- Set spending limits
- Configure notifications

## Quick Reference

### Essential Commands

```bash
# Push workflow files to GitHub
git add .github/
git commit -m "Add AI workflow"
git push

# Check if workflow file exists
ls -la .github/workflows/ai-issue-handler.yml

# Test workflow locally (requires API keys)
python .github/scripts/ai_issue_processor.py
```

### Key Files

- `.github/workflows/ai-issue-handler.yml` - Main workflow definition
- `.github/scripts/ai_issue_processor.py` - AI processing script
- `.github/GITHUB_AI_WORKFLOW.md` - This documentation file

### Important URLs

- GitHub Secrets: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`
- GitHub Actions: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`
- OpenAI API Keys: `https://platform.openai.com/api-keys`
- Anthropic API Keys: `https://console.anthropic.com/settings/keys`

## Getting Help

If you're stuck:

1. **Check the workflow logs**: Go to **Actions** → Click on the failed run → Review the logs
2. **Review this documentation**: Make sure you followed all setup steps
3. **Check GitHub Actions status**: Visit [githubstatus.com](https://www.githubstatus.com/) to see if GitHub is having issues
4. **Verify API provider status**: Check OpenAI or Anthropic status pages
5. **Review the issue description**: Make sure it's clear and actionable

## Next Steps

After setup is complete:

1. ✅ Create a test issue to verify everything works
2. ✅ Review the AI-generated PR before merging
3. ✅ Provide feedback in issues to improve AI understanding
4. ✅ Monitor costs and usage
5. ✅ Enjoy automated AI assistance with your development workflow!
