# ADR 0032: Posting a verification run is its own step, with its own token

Status: Proposed with the PR for #281. Merging that PR accepts the contract below.

## Context

ADR 0031 builds a verification run as a document and sends nothing. The plan's decisions 17 and 19 say that nothing is transmitted automatically and that only CI pushes to the graph. The engine accepts a run only from the exact `service` role, stores it immutably, and answers an identical re-send with the stored run.

GovKit's existing graph client is read-only by construction, and its credential, `GOVKIT_PDG_TOKEN`, is given to a pull request job.

The maintainer decided on 2026-11-27:

- The CI step is its own template for both providers. It runs on the default branch only and does nothing until its settings exist.
- A separate service token.
- The baseline tag is a setting a person maintains.
- Nothing to send passes with a notice. A refusal fails the step.

## Decision

1. **A new command, `govkit verification-run push --run FILE`.** It validates the document again and posts its `request`. It builds nothing and reads no feature.
2. **A separate module.** `verification_push.py` holds the one write. `pdg_client.py` stays read-only.
3. **The address and the token come from the environment.** `GOVKIT_PDG_URL` and `GOVKIT_PDG_SERVICE_TOKEN`. Neither is an option, and neither is read from the repository.
4. **Plain https, no redirect.** A redirect is not followed, since the token would go to an address nobody stated.
5. **A refusal is an answer; silence is not.** A 4xx is the graph's refusal. A 5xx, a timeout, a redirect, or a success whose body is not the stored run under the same reference is no answer.
6. **Response text is data.** The command prints the status, a reason code and the identifiers or keys the graph named, each reduced to a bounded plain string. It prints nothing else from a response.
7. **Exit status.** 0 recorded, already recorded, or nothing to send; 1 refused; 2 could not start; 3 no usable answer.
8. **The template.** `verification-run.yml` for GitHub and Azure: tests, record, build, post. It triggers on pushes to the default branch, is skipped while `GOVKIT_BASELINE_TAG` is unset, and maps the service token into the last step only. It is in no manifest; a project copies it.
9. **The run reference is the provider's run and attempt.** A re-run of one attempt re-sends the same run.

## Alternatives considered

- **Steps in the evidence gate.** Every project with that gate would carry graph steps, and a pull request job would hold a default-branch-only tail.
- **Reuse `GOVKIT_PDG_TOKEN`.** The pull request gate would hold write authority.
- **The newest tag in Git as the baseline.** A tag that exists is not necessarily indexed, and a release tag could be picked.
- **Ask the graph for its latest baseline.** That read needs a second token with another role.
- **Fail when there is nothing to send.** The job would be red after every scenario edit until a new baseline is indexed.
- **Post with `curl` from the template.** Refusals would be handled by shell in two files and not by tested code.
- **Retry inside the command.** A caller's pipeline already has retries, and exit status 3 says when one is safe.

## Consequences

- **The step is not a gate.** It reports to the graph; it judges nothing.
- **A posted run cannot be withdrawn.** The template therefore never runs for a pull request.
- **A stale `GOVKIT_BASELINE_TAG` sends less, not wrong.** Results the tag does not hold at that revision are left out. A tag the graph has not indexed is refused by the graph.
- **The post is not verified against a real graph**, and the templates have not run on either provider.
- **The template installs a released GovKit.** It needs the first release that has this command.
- The option name, the two environment names and the exit codes are a public contract: add, never rename.
