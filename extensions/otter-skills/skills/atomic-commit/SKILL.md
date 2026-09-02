---
name: atomic-commit
description: Create honest atomic Git commits by choosing one coherent work batch before editing, keeping the whole repository green, resolving every untracked file, staging the entire root with `git add .`, and pausing for human review before committing. Use when starting commit-sized work, completing a demonstrable implementation slice, running a series of refactorings, preparing or making a commit, or discussing atomic commits and trustworthy history. Do not use partial staging or retrospectively compose commits from an already mixed working tree.
---

# Atomic Commit

Preserve historical truth: every commit must be a complete repository state that actually existed on disk, was tested in exactly that form, and was vetted by a human. A stranger must be able to check out any commit and encounter a coherent change with green tests.

Atomicity begins when choosing the work, not when staging it. A small-looking commit assembled afterward from selected hunks is not atomic.

## Non-negotiable invariants

- Green before every commit is absolute. Never create a failing, WIP, checkpoint, or “fixed by the next commit” commit.
- Incremental refactoring, tests, prescribed scans, and documentation are pre-commit work. Complete and verify them before presenting the feature commit for review.
- Commit the entire working-directory state. Never use partial staging, path-limited staging, `git add -p`, or temporary reversal to manufacture commit boundaries.
- Run all Git and verification commands from the repository root. Establish it with `git rev-parse --show-toplevel`; do not assume the current directory is the root.
- Every untracked file receives an explicit disposition: add, ignore, or delete. Make evident decisions autonomously; ask the human only when the correct disposition is uncertain.
- A human reviews the complete proposed commit after verification and before `git commit`.
- Human review is part of the rapid local microcommit loop, not a reason to enlarge batches or postpone a completed green step. Many human-reviewed commits in a day are entirely consistent with this skill.
- Use a Conventional Commits message that truthfully describes the whole state.

## Choose the batch before editing

Begin from a clean, green repository. If it is dirty, do not add another intention. Finish and commit the existing state through this protocol, or ask the human how to resolve it.

Choose one meaningful, bounded change and state its intention. Then perform only that batch. Keep the batch small enough to understand, test, and review as a whole.

A feature batch is coherent when it contains everything needed to leave that feature complete and trustworthy: its behavior change, incremental refactoring, tests, prescribed scans, and relevant documentation. These are supporting parts of one atomic feature commit, not separate intentions that must be split into preparatory or follow-up commits.

If several logical changes nevertheless accumulate, acknowledge the broader batch and commit the complete state together. Do not split, selectively stage, or reconstruct it into cleaner-looking commits: those synthetic snapshots were not the states tested on disk. Describe the combined state honestly and improve batch discipline on the next change.

## Recognize the commit point

Completion of a demonstrable implementation slice, iteration, or story triggers the complete-state commit protocol only after its incremental refactoring, tests, prescribed scans, and documentation updates are complete. Demonstrable means the resulting behavior can be shown or verified as an end-to-end outcome, not merely that an internal task list is exhausted. Do not begin the next slice while the completed one remains uncommitted.

Treat refactoring as a series of small experiments. After each refactoring run, execute the prescribed tests and return the whole repository to green before proceeding. Then show the human the result and ask whether the representation is sufficient or whether another refactoring run is warranted. The human decides when the refactoring is enough; the agent must not silently extend the series or declare completion on its own. When the human says it is enough, enter the complete-state commit protocol for the whole current state.

If a refactoring run is not an improvement, undo that experiment while preserving unrelated work, restore green, and present the result again. Do not stack further refactorings onto an unverified or failing state.

## Complete-state commit protocol

Perform the protocol from the repository root.

1. Confirm the intended batch is complete.
2. List all untracked, non-ignored files, for example with `git ls-files --others --exclude-standard`.
3. Inspect each file and decide: **add**, **ignore**, or **delete**. Ask only about genuinely uncertain cases.
4. Apply every delete and `.gitignore` decision. Use safe, recoverable deletion where available and do not delete uncertain files.
5. Inspect the complete working tree with `git status --short` and the relevant full diffs.
6. Run the repository's complete prescribed test, scan, and verification suite against this resulting state. Every check must be green. If verification cannot complete or any check fails, do not commit.
7. Re-list untracked files and inspect the complete status after verification. Tests and formatters sometimes create or modify files. Classify anything new; if cleanup or another action changes the repository state, repeat verification and this check until the green state is stable.
8. Run `git add .` from the repository root, exactly—not from a subdirectory and not with narrower path arguments.
9. Inspect `git status --short` and the complete staged diff (`git diff --cached`). Confirm that the staged snapshot contains the entire intended working state and no unexplained file.
10. Present the human with:
   - the complete status and reviewable staged change;
   - every untracked-file disposition;
   - the exact verification commands and green results;
   - the proposed Conventional Commits message.
11. Pause. Run `git commit -m "<type>[optional scope]: <description>"` only after explicit human approval.

Staging and inspection must not change repository files. If human review or any later action changes a file, the reviewed and tested state is stale: restart the untracked-file check, verification, `git add .`, staged review, and approval.

After committing, confirm the working tree is clean and report the commit identifier, message, and verification performed.

## History rewriting and commit-producing Git operations

Frown upon amend, rebase, squash, cherry-pick, and other history rewriting because they can manufacture commits that never independently existed and passed tests in their final context. Prefer a forward series of real, complete, vetted changes.

When rewriting is explicitly required, the same invariants still apply to every final commit. Prevent the operation from auto-committing where possible, materialize the complete final tree on disk, resolve all untracked files, run the full prescribed verification, stage the whole root with `git add .`, present the exact result for human review, and only then create that commit. A sequence of rewritten commits must be checked and tested one final commit at a time; testing only the sequence endpoint is insufficient.

Do not claim a rewritten commit was vetted merely because its source commit or aggregate result once passed. The exact final state is the evidence.

## Stop conditions

Do not commit when any of these is true:

- the repository was not green in the exact state now staged;
- verification was incomplete, skipped, or changed after it ran;
- an untracked file lacks a disposition;
- tracked or staged changes are unexplained;
- the command is being run below the repository root;
- the human has not reviewed and explicitly approved the complete state;
- the proposed message conceals the actual breadth or intention of the batch.
