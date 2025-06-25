# Security Fix: Exposed API Key

## Issue
An Anthropic API key was accidentally committed to the repository in `config.json` file.

## Immediate Actions Taken
1. Removed the API key from `config.json`
2. Created `.env.example` file to document environment variables
3. Added comment in config.json to use environment variables

## Required Actions

### 1. Revoke the Exposed Key
**CRITICAL**: The exposed Anthropic API key MUST be revoked immediately:
- Go to https://console.anthropic.com/settings/keys
- Revoke the key starting with `sk-ant-api03-9WjZx9l...`
- Generate a new API key

### 2. Clean Git History
Since the key is already in the git history, we need to remove it completely:

```bash
# Option 1: If you haven't pushed many commits after this
git reset --hard c300a7c  # Reset to commit before the key was added
# Then cherry-pick the good commits

# Option 2: Use BFG Repo Cleaner (recommended)
# Download BFG from https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --replace-text passwords.txt privategpt
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Option 3: Interactive rebase to edit the specific commit
git rebase -i 5d56591^
# Mark the commit as 'edit', then amend it to remove the key
```

### 3. Force Push (after cleaning)
```bash
git push --force-with-lease origin main
```

### 4. Set Up Environment Variables
Create a `.env` file (never commit this!):
```bash
cp .env.example .env
# Edit .env and add your new API keys
```

### 5. Update .gitignore
Ensure `.env` is in `.gitignore`:
```bash
echo ".env" >> .gitignore
```

## Prevention
1. **Never put API keys in config files** that are committed
2. **Always use environment variables** for sensitive data
3. **Use git-secrets** or similar tools to prevent accidental commits
4. **Enable GitHub secret scanning** on the repository

## Configuration Best Practice
The application already supports environment variables. The settings system will:
1. First check environment variables
2. Fall back to config.json values
3. Use defaults if neither is set

So you can safely set `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` as environment variables.