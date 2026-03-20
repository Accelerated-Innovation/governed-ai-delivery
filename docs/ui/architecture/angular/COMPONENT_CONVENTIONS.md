# Component Conventions — Angular

---

## 1. Component Types

### Feature Components
Live in `src/features/<feature>/components/`. Owned by the feature. Not importable by other features.

### Shared Components
Live in `src/shared/components/`. Truly generic UI primitives. Must not import from `features/`. Promoted via ADR.

---

## 2. Component Structure

Use standalone components (Angular 17+):

```typescript
@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './user-profile.component.html',
  styleUrl: './user-profile.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserProfileComponent {
  // inject query functions — not services that call APIs directly
  readonly profile = injectUserProfile(this.userId);

  @Input({ required: true }) userId!: Signal<string>;
}
```

### Rules

- Always use `ChangeDetectionStrategy.OnPush`
- Always use standalone components — no NgModule declarations
- One component per file
- Templates in separate `.html` files — no inline templates for non-trivial components
- Styles in separate `.css` files — no inline styles

---

## 3. Inputs and Outputs

- Use `input()` signal-based inputs (Angular 17+) over `@Input()` decorator where possible
- Use `output()` over `@Output() EventEmitter` for new code
- Required inputs declared with `input.required<T>()`
- Callback outputs prefixed with `on` (e.g., `onSubmit`, `onClose`)

```typescript
// Preferred — signal inputs/outputs
readonly userId = input.required<string>();
readonly onSave = output<UserProfile>();

// Legacy — still valid but prefer signal-based for new code
@Input({ required: true }) userId!: string;
@Output() onSave = new EventEmitter<UserProfile>();
```

---

## 4. Template Rules

- No business logic in templates — use computed signals or component methods
- No direct API calls or service injections in templates
- Use `@if`, `@for`, `@switch` (Angular 17+ control flow) over `*ngIf`, `*ngFor`
- Always provide `track` expression in `@for` — never track by index for mutable lists

```html
<!-- Good -->
@for (user of users(); track user.id) {
  <app-user-card [user]="user" />
}

<!-- Bad -->
@for (user of users(); track $index) { ... }
```

---

## 5. Loading and Error States

Handle in the component that calls the query — not inside the query itself:

```html
@if (profile.isPending()) {
  <app-spinner />
} @else if (profile.isError()) {
  <app-error-message />
} @else {
  <app-profile-card [profile]="profile.data()!" />
}
```

---

## 6. Naming

- Components: PascalCase class, kebab-case selector (`UserProfileComponent`, `app-user-profile`)
- Query functions: camelCase prefixed with `inject` (`injectUserProfile`)
- Signal stores: PascalCase class suffixed with `Store` (`UserFilterStore`)
- API services: PascalCase class suffixed with `Api` (`UserApi`)
- Files: kebab-case with type suffix (`user-profile.component.ts`, `user.api.ts`)

---

## 7. Forbidden Patterns

- `any` type — use `unknown` and narrow properly
- `ngOnInit` for data fetching — use TanStack Query
- Direct `HttpClient` calls in components — use the API layer
- `Default` change detection — always use `OnPush`
- Inline NgModule-based components — use standalone only
- Business logic in templates — extract to computed signals or methods
