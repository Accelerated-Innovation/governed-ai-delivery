---
name: govkit-pr-author
description: Author and open a governed pull request that carries its governance evidence. Use when the user asks to open a PR, create a pull request, or invokes /govkit-pr-author.
---

# PR Author

Author the pull request for the change on the current branch, then open it. A governed PR does two jobs an ordinary PR does not: it names the lane the change went through, and it links the records that let a reviewer check the claims in seconds instead of reconstructing them from the diff.

## Inputs to read

Repository facts:
- `.govkit/marker.json` — read `level`, `options.type`, and `options.ci`. These decide which artifacts exist to link and which CI platform receives the PR. Do not assume; read the recorded values.

The change's governing records, by lane:
- Feature lane: `features/<feature_name>/` — the acceptance criteria, NFRs, preflight, and plan for the feature this branch implements
- Fix lane: `fixes/<id>/fix.yaml` — the single record for a defect that restores established behavior
- ADRs: `docs/{{docs_area}}/architecture/ADR/` — any decision this change depends on

Approval policy (Level 4+):
- `governance/approval_policy.yaml` — who may approve; relevant when the change carries an ADR

## Determine the lane first

Read the branch's diff against the default branch and decide which lane this change went through:

1. **Feature lane** — the change implements a feature under `features/`. Name the feature folder.
2. **Fix lane** — the change carries a `fixes/<id>/fix.yaml` restoring established behavior.
3. **Architecture-governed (Level 3)** — the recorded `level` is 3: there is no `features/` workflow, and a source change is governed by the architecture contracts alone. Describe the change against those contracts and skip the artifact links.
4. **Ungoverned change** — docs, tooling, or configuration that no lane governs. Say so plainly in the PR body rather than dressing it as one.

A source change with no feature folder and no fix record at Level 4+ is a gap, not a fifth lane. Stop and say which artifacts are missing, and point to the planning skills — do not open a PR that launders an ungoverned source change past the gates.

## Preflight before opening

Run what can be run, and record what happened — not what you hope the gates will find:

1. Run the project's test suite. A red suite means no PR; report the failure instead.
2. At Level 4+, run `govkit validate --target .` and resolve anything it reports.
3. Fix lane: confirm the reproduction test failed before the fix and passes after. That red-green cycle is a claim the PR body makes; make it true before making it.
4. If the change carries an ADR, its status is `Proposed`. Do not write `Accepted` — that state is derived from an approver's review, never typed.

## Author the PR

**Title** follows the commit convention: `type(scope): description` with types `feat|fix|docs|test|refactor|chore`. The scope is the feature name or fix id where one exists.

**Body** carries, in order:

- **Summary** — what changed and why, in the language of the affected behavior
- **Lane** — feature `<feature_name>`, fix `<id>`, architecture-governed (Level 3), or ungoverned, with one line saying why the lane fits
- **Governing artifacts** — repo-relative links to the feature folder or fix record, and to any ADR the change depends on (with its actual status)
- **Evidence** — what was run and what it reported: the test command and its result, `govkit validate` output at Level 4+, the red-before-green confirmation for a fix
- **Gates** — the installed CI gates this PR will trigger, so the reviewer knows what the platform checks and what remains theirs to judge

Claim only what ran. A gate that has not run yet is listed as pending, not passed; a declaration the tooling cannot verify (a fix restores established behavior, an eval threshold will hold) is stated as a declaration. The PR body is where self-certification is easiest and costs the most.

## Open the PR

1. Never commit to or push the default branch. If the work sits on it, create a feature branch and move the changes there first — a push to the default branch bypasses the very gates this skill exists to feed.
2. Confirm the working tree is clean. Increments are reviewed and committed as they land; uncommitted work here means an increment has not had that review. Hand it back to the user to review and commit — do not batch-commit accumulated work into manufactured increment commits.
3. Push the branch.
4. Open the PR with the platform CLI that matches `options.ci` — `gh pr create` for GitHub, `az repos pr create` for Azure DevOps — using the authored title and body.
5. If no platform CLI is available, or pushing is not permitted in this environment, stop after authoring: output the branch name, title, and body ready to paste, and say that opening the PR is the remaining step.

Never merge. Opening the PR is where this skill's authority ends — the gates and the approvers named in the policy own what happens next.
