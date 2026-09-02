# Digest: Context Creates Clarity (ch: context)

## The hierarchy
Names do not exist alone. Every name lives inside:
`system → module/package → file → class → method → variable`

Each outer layer provides context. Inner names need not (should not) repeat it.

## The redundancy test
> Is this word already present in the enclosing class/method/module name?
> If yes, drop it from the member name.

```java
// Over-specified — every name repeats "employee" and "payroll"
class EmployeePayrollCalculator {
    Money calculateEmployeeGrossPay(Employee employee, PayPeriod payPeriod) {
        BigDecimal employeeHourlyRate = employee.getEmployeeHourlyRate();
```

```java
// Context-aware — class name carries "employee" and "payroll"
class EmployeePayrollCalculator {
    Money calculateGrossPay(Employee employee, PayPeriod payPeriod) {
        BigDecimal rate = employee.getHourlyRate();
```

## Windshield naming
Name by **purpose** (what it is *for*), not composition (what it is *made of*).
- "windshield" → shields from wind (purpose)
- "front glass" → glass at the front (composition)

Apply: `tail` in `bite_head_off()` could be `result`; ask what the caller will
*do* with it, not what it structurally is.

## Domain terms
Use the vocabulary domain experts use. `mrn`, `apy`, `sku`, `commit_hash` —
these are **profitable struggle** (see `ch-familiarity.md`). When developers
learn the term, it pays dividends everywhere: source, UI, discussions.

## Noise words to avoid
`data`, `info`, `record`, `manager`, `processor` almost never add meaning.
`CustomerData`, `CustomerInfo`, `CustomerRecord` in the same codebase = garbage.
`ProcessingResult` on a financial enum that has `PAYMENT_FAILED` is too generic
— it is probably `TransactionResult`.

## When a name must travel
A class or function used *outside* its defining module must carry enough context
to be understood alone. Some redundancy is then justified.
- Within `email` module: `Validator` is fine.
- Outside: alias it: `from email import Validator as email_validator`.
- If aliasing is frequent and consistent, that's a signal to rename the class.

## Mathy vs. prosey
In mathematical or algorithm contexts, conventional single-letter variables
(`x`, `y`, `i`, `j`, `a`, `b`, `c` in quadratic formula) may be the
clearest choice. Let the mathematical domain win.

## Over-contextualization anti-pattern
Pattern-combination names (`StrategyManagerFactory`, `DataProcessorHelper`) and
noise-word hybrids impart little domain meaning. Strip them.

## Practical guidelines (from manuscript)
1. Trust your context — don't repeat what's already given.
2. Consider the reader's journey through the hierarchy.
3. Match domain vocabulary — use what domain experts say.
4. Embrace minimal names in minimal contexts.
5. Evolve names when code moves to a new context (refactoring/extraction).
