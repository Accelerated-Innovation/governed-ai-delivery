Feature: Invoice approval routing

  @rule:invoice-approval-threshold
  Rule: Invoices of 10,000 or more require finance manager approval

    @mvp @scenario:approval-routing-by-amount
    Scenario Outline: Invoice amount decides the approval path
      Given an invoice of <amount>
      When it is submitted
      Then it is routed to <approver>

      Examples:
        | amount | approver        |
        | 9999   | team lead       |
        | 10000  | finance manager |

    @nfr-performance
    Scenario: Routing completes within 200 ms at p95
      Given 50 invoices
      When they are submitted
      Then routing takes at most 200 ms at p95

    Scenario: A rejected invoice returns to its author
      Given a rejected invoice
      Then it is returned to its author
