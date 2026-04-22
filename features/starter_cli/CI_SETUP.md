# CI Workflow Setup

This guide explains how to configure GitHub Actions and Azure Pipelines for your project after installing governance artifacts via `govkit apply`.

## Repository Scope Validation

**Why:** Ensures features explicitly declare which repositories own which parts of the implementation. Prevents agents from writing code in the wrong repository.

**File:** `.github/workflows/repo-scope-check.yml` (GitHub) or `azure-pipelines-repo-scope.yml` (Azure)

**Setup:**

1. Copy the template from `governance/ci/github/repo-scope-check.yml` (GitHub) or `governance/ci/azure/repo-scope-check.yml` (Azure) to your `.github/workflows/` directory

2. **Set your repository owner name:**
   
   Edit the workflow file and find this line:
   ```yaml
   REPO_OWNER: YOUR_REPO_NAME
   ```
   
   Change `YOUR_REPO_NAME` to your repository's actual name. Examples:
   - `cli-service`
   - `task-runner`
   - `admin-tool`
   - `command-executor`

3. Commit and push

4. The workflow will run automatically on all PRs that modify `features/*/nfrs.md`

**When it passes:**
- All features have a "Repository Scope" section in their `nfrs.md`
- Single-repo features are marked as such
- Multi-repo features list this repository as an owner

**When it fails:**
- A feature is missing the Repository Scope section
- A multi-repo feature doesn't list this repository as owner

Fix by editing the feature's `nfrs.md` to complete the "Repository Scope" section.

---

## Other CI Workflows

Once you've installed governance artifacts, ensure these additional workflows are configured:

- **quality-gate.yml** — Code quality, architecture boundaries, security scans
- **eval-gate.yml** (L4+ only) — Evaluation prediction thresholds
- **l3-quality-gate.yml** (L3 only) — Basic quality checks for spec-driven development

See `ci/README.md` in the governance template repository for full documentation.

---

## Quick Checklist

- [ ] Copy `repo-scope-check.yml` to `.github/workflows/` (GitHub) or configure in Azure Pipelines
- [ ] Set `REPO_OWNER` variable to your repository name
- [ ] Commit and push
- [ ] Verify the workflow runs on next PR to `features/*/nfrs.md`
- [ ] Configure other CI workflows (quality-gate, eval-gate, etc.)
