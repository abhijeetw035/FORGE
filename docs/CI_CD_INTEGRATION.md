# CI/CD Integration Guide

This guide explains how to integrate FORGE into your GitHub Actions workflow to automatically analyze PRs.

## 🎯 What It Does

The FORGE GitHub Action:
- ✅ Analyzes every pull request automatically
- ✅ Identifies changed files with high churn scores
- ✅ Posts risk warnings as PR comments
- ✅ Helps reviewers focus on critical files

## 📋 Prerequisites

1. **FORGE Instance Running**
   - Deploy FORGE on a server (or run locally for testing)
   - Note the API URL (e.g., `https://forge.yourcompany.com`)

2. **Repository Analyzed**
   - Submit your repository to FORGE first
   - Note the repository ID from the response

## 🚀 Setup Steps

### Step 1: Configure GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `FORGE_API_URL` | Your FORGE API endpoint | `https://forge.yourcompany.com` |
| `FORGE_REPO_ID` | Repository ID from FORGE | `3` |

### Step 2: Copy Workflow File

The workflow file is already in your repo at:
```
.github/workflows/forge-analysis.yml
```

If setting up in a different repo, copy this file there.

### Step 3: Enable Workflow

1. Go to **Actions** tab in GitHub
2. Find "FORGE Code Analysis" workflow
3. Enable it if prompted

### Step 4: Test It!

1. Create a test branch
2. Modify a high-churn file (like `miner/services/ast_parser.py`)
3. Open a pull request
4. Watch FORGE comment with risk analysis!

## 📊 Example Output

The workflow will comment on your PR:

```markdown
## 🔥 FORGE Code Analysis

### ⚠️ Critical Risk Files

These files have extremely high churn (>100 modifications). Review carefully:

- 🔴 `miner/services/ast_parser.py` (Churn: 142, Size: 1587 LOC) - **CRITICAL RISK**

**Recommendation**: Consider refactoring or adding comprehensive tests.

### 🟠 High Risk Files

These files have significant churn (>50 modifications):

- 🟠 `api/routes/repositories.py` (Churn: 72, Size: 702 LOC) - **HIGH RISK**
- 🟠 `miner/services/git_service.py` (Churn: 68, Size: 481 LOC) - **HIGH RISK**

**Recommendation**: Extra scrutiny during code review.

---

*Powered by FORGE - Code Entropy Engine*
*Churn Score = Number of historical modifications | Size = Lines of Code*
```

## 🎨 Customization

### Change Risk Thresholds

Edit `.github/workflows/forge-analysis.yml`:

```yaml
# Critical: score > 100 (default)
if [ "$SCORE" -gt 100 ]; then

# High risk: score > 50 (default)
elif [ "$SCORE" -gt 50 ]; then
```

Adjust these numbers based on your codebase:
- Large projects: Higher thresholds (150, 75)
- Small projects: Lower thresholds (50, 25)

### Add More File Types

Edit the `files` filter:

```yaml
files: |
  **/*.py
  **/*.js
  **/*.ts
  **/*.java
  **/*.go
  **/*.rb     # Add Ruby
  **/*.php    # Add PHP
```

### Skip Specific Files

Add exclusions:

```yaml
files: |
  **/*.py
files_ignore: |
  **/test_*.py
  **/*_test.py
```

## 🔧 Advanced Configuration

### Self-Hosted Runner

For private networks, use a self-hosted runner:

```yaml
jobs:
  analyze:
    runs-on: self-hosted  # Instead of ubuntu-latest
```

### Multiple Repositories

Create a matrix strategy:

```yaml
strategy:
  matrix:
    repo: [repo1, repo2, repo3]
env:
  FORGE_REPO_ID: ${{ matrix.repo }}
```

### Webhook Alternative

Instead of polling, set up a webhook:

```yaml
on:
  workflow_dispatch:
    inputs:
      repo_id:
        description: 'FORGE Repository ID'
        required: true
```

## 🐛 Troubleshooting

### "No data returned from FORGE"

**Problem**: Workflow can't reach FORGE API

**Solutions**:
1. Check `FORGE_API_URL` secret is correct
2. Ensure FORGE is publicly accessible or use self-hosted runner
3. Verify FORGE_REPO_ID exists: `curl $FORGE_API_URL/repositories/$FORGE_REPO_ID`

### "jq: command not found"

**Problem**: Ubuntu runner missing jq

**Solution**: Add installation step:
```yaml
- name: Install jq
  run: sudo apt-get update && sudo apt-get install -y jq
```

### "Permission denied" on comment

**Problem**: GITHUB_TOKEN doesn't have write permissions

**Solution**: Verify workflow permissions:
```yaml
permissions:
  contents: read
  pull-requests: write  # Required for commenting
```

### No files detected

**Problem**: Changed files don't match filters

**Solution**: Check file extensions in `files` filter match your changes

## 📈 Metrics to Track

Monitor your workflow effectiveness:

1. **False Positive Rate**: Files flagged but not risky
2. **True Positive Rate**: Correctly identified risky changes
3. **Developer Feedback**: Are warnings helpful?
4. **Review Time**: Does it reduce review iterations?

## 🎯 Best Practices

### Do's ✅
- **Start with high thresholds** - Avoid alert fatigue
- **Review metrics monthly** - Adjust thresholds based on team feedback
- **Use with other tools** - Combine with linters, security scanners
- **Educate the team** - Explain churn scores in team meetings

### Don'ts ❌
- **Don't block merges** - Use as guidance, not gates
- **Don't shame developers** - High churn isn't always bad
- **Don't ignore context** - New features naturally increase churn
- **Don't set thresholds too low** - Focus on genuinely risky files

## 🚀 Next Steps

1. **Week 1**: Run silently, observe patterns
2. **Week 2**: Adjust thresholds based on feedback
3. **Week 3**: Enable PR comments
4. **Week 4**: Train team on interpreting results

## 💡 Pro Tips

**Combine with Branch Protection**
```yaml
# Require manual approval for critical files
if: contains(steps.forge-analysis.outputs.critical_files, '🔴')
```

**Send Slack Notifications**
```yaml
- name: Notify Slack
  if: steps.forge-analysis.outputs.critical_files != ''
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {"text": "⚠️ PR #${{ github.event.number }} touches critical files!"}
```

**Generate Reports**
```yaml
- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: forge-analysis
    path: forge-report.json
```

## 🤝 Contributing

Improve the workflow:
1. Fork the repository
2. Modify `.github/workflows/forge-analysis.yml`
3. Test with your PRs
4. Submit improvements!

---

**Need Help?** Open an issue at [abhijeetw035/FORGE](https://github.com/abhijeetw035/FORGE/issues)
