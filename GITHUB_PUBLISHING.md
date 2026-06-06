# ZeroTouch SRE GitHub Publishing

The project is ready to publish as a standalone public repository.

## Current Local Repo

ZeroTouch SRE should be committed from:

```powershell
C:\Users\prati\Downloads\Projects\ZeroTouch SRE
```

The `.gitignore` excludes:

- `.env`
- `.venv/`
- local reports
- generated demo artifacts
- logs and Python caches

## Publish With GitHub CLI

Authenticate once:

```powershell
gh auth login
```

Create and push the public repo:

```powershell
gh repo create zerotouch-sre --public --source . --remote origin --push
```

The resulting repository URL is the Devpost `Public repository URL`.

## Post-Publish Checklist

- Confirm `README.md`, `MIT-LICENSE.txt`, `DEVPOST_SUBMISSION.md`, and `CLOUD_RUN_DEPLOYMENT.md` are visible.
- Confirm `.env` is not present in the repository.
- Confirm the hosted URL in the README works:
  `https://zerotouch-sre-971465910048.us-central1.run.app/health`
