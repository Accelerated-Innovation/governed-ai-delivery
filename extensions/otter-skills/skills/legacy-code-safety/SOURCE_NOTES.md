# SOURCE_NOTES — legacy-code-safety

This skill synthesizes Michael Feathers' legacy-change mechanics, Emily Bache and Llewellyn Falco's approval-testing practice, GeePaw Hill's microtest rhythm and incremental switchover, and Tim Ottinger's clean-start, feedback, checkpoint, representation, integration, and delivery disciplines.

## Design choices

- The skill ends when a trustworthy boundary exists and the requested behavior can enter `unit-testing`; it does not create a competing TDD workflow.
- Characterization, dependency breaking, and incremental switchover are separate references because each is loaded only for its corresponding obstacle.
- The entrypoint emphasizes invariants and decisions rather than reproducing Feathers' full catalog of dependency-breaking techniques.
- Approval artifacts require intentional inspection; the skill does not permit blind snapshot updates.
- Incremental switchover permits named temporary duplication when it makes a large live-code transition safer, balancing SPOT against delivery risk.
- Commit, integration, and external-release actions remain subject to user authorization and project practice.
