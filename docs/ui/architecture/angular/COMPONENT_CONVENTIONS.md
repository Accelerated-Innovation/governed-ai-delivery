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

---

## 8. Hard Rules — Boundaries and Dependencies

These rules enforce architecture boundaries and prevent common anti-patterns.

### No Direct API Calls
- **Forbidden:** `HttpClient` injection, `fetch`, or direct query calls at the top level of a component file
- **Why:** Data fetching belongs in services and query functions, not components
- **How:** Wrap all API logic in a query function (e.g., `injectUserProfile`) that handles fetching and caching

```typescript
// Bad
@Component({...})
export class UserProfileComponent {
  constructor(private http: HttpClient) {}
  
  ngOnInit() {
    this.http.get(`/api/users/${this.userId()}`).subscribe(user => {
      this.user = user;
    });
  }
}

// Good
@Component({...})
export class UserProfileComponent {
  readonly profile = injectUserProfile(this.userId);
  // Query function handles fetching, caching, and state
}
```

### No Data Transformation in Components
- **Forbidden:** Deriving values from raw API responses in the component
- **Why:** Components should work with pre-shaped data; transformation is a query/selector concern
- **How:** Use TanStack Query's `select` option or computed signals to shape data before the component uses it

```typescript
// Bad — transformation in component
const profile = injectUserProfile(this.userId);
readonly fullName = computed(() => 
  `${profile.data()?.firstName} ${profile.data()?.lastName}`
);

// Good — transformation in query function
const profile = injectUserProfile(this.userId);
// The query function already returns shaped data via select()
```

### No Business Logic
- **Allowed:** Conditional rendering based on data state (`isPending()`, `isError()`)
- **Forbidden:** Deriving values, calculating totals, applying business rules
- **How:** Put business logic in domain services or query functions; components only render

```typescript
// Bad — business logic in component
@Component({...})
export class OrderSummaryComponent {
  readonly items = input.required<OrderItem[]>();
  readonly subtotal = computed(() => 
    this.items().reduce((sum, item) => sum + item.price * item.qty, 0)
  );
  readonly tax = computed(() => this.subtotal() * 0.08);
  readonly total = computed(() => this.subtotal() + this.tax());
}

// Good — logic in a service
@Component({...})
export class OrderSummaryComponent {
  readonly items = input.required<OrderItem[]>();
  readonly calculations = injectOrderCalculations(this.items);
  // calculations contains { subtotal, tax, total }
}
```

### No Cross-Feature Imports
- **Forbidden:** Importing from another feature's `components/`, `services/`, `store/`, or `api/`
- **Why:** Prevents tight coupling and preserves feature boundaries
- **How:** Share types via `src/shared/types/`; share components via `src/shared/components/`; communicate via props and input/output signals

```typescript
// Bad
import { UserCard } from "../features/users/components/user-card.component";
import { injectUserList } from "../features/users/api/user.api";

// Good — use shared components or define local composition
import { Card } from "@shared/components/card.component";
```

### No Direct Store Writes
- **Forbidden:** Calling `store.setState()` or raw Zustand/Pinia mutations from event handlers
- **Why:** Makes state transitions implicit and hard to trace
- **How:** Export named actions from the store and call those

```typescript
// Bad
readonly filterStore = inject(FilterStore);
readonly onFilterChange = output<string>();

onFilterChange.emit('active');
// Then in handler:
this.filterStore.setState({ filter: 'active' });

// Good
readonly filterStore = inject(FilterStore);

setFilter(filter: string) {
  this.filterStore.setFilter(filter); // Named action
}
```

---

## 9. Testing

All components must be tested with **Vitest + Angular Testing Utilities**.

### Requirements

- **Test behavior, not implementation** — query by role, label, or accessible text
- **No snapshot tests** — snapshots become stale and don't verify behavior
- **No implementation details** — don't test internal component state or method calls
- **FIRST principles** — all tests must satisfy Fast, Isolated, Repeatable, Self-Verifying, Timely (see `docs/ui/evaluation/FIRST_SCORING_RUBRIC.md`)
- **Axe accessibility check** — run `axe-core` in every component test to catch WCAG violations

### Example

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { screen, render } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { UserProfileComponent } from './user-profile.component';

describe('UserProfileComponent', () => {
  it('displays user name when data loads', async () => {
    // Arrange
    const profile = { id: '1', firstName: 'Alice', lastName: 'Smith' };
    // Mock the query function
    vi.mocked(injectUserProfile).mockReturnValue({
      data: () => profile,
      isPending: () => false,
      isError: () => false,
    });

    // Act
    const { container } = await render(UserProfileComponent, {
      componentProperties: { userId: signal('1') },
    });

    // Assert
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();

    // Accessibility check
    const { axe } = await import('vitest-axe');
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('shows loading spinner while data fetches', async () => {
    // Mock pending state
    vi.mocked(injectUserProfile).mockReturnValue({
      data: () => undefined,
      isPending: () => true,
      isError: () => false,
    });

    await render(UserProfileComponent, {
      componentProperties: { userId: signal('1') },
    });

    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });
});
