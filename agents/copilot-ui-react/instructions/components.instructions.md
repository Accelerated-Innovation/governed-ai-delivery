---
applyTo: "**/components/**"
---

Follow the component conventions defined in `docs/ui/architecture/COMPONENT_CONVENTIONS.md`.

All components in `**/components/**` must:

- Be pure view components — no direct API calls, no `fetch`, no `useQuery`
- Receive all data and callbacks via props or custom hooks
- Contain no business logic or data transformation — fix the hook if the shape is wrong
- Not import from another feature's `components/`, `hooks/`, `store/`, or `api/`
- Have all props typed with a local `interface Props {}`
- Use React Testing Library for tests — query by role, label, or text only
- Include an `axe` accessibility check in every component test

All components are views. They render. They do not fetch, transform, or decide.
