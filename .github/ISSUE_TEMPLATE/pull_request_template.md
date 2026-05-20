<!-- Thank you for contributing! Pick the appropriate type below and fill out
     the relevant section. Sections that don't apply can be deleted. -->

## Type of change

- [ ] `merchant:new` — adding a new merchant profile
- [ ] `merchant:variant` — adding a regional/legal-form variant
- [ ] `merchant:fix` — fixing a bug in an existing profile
- [ ] `merchant:layout-update` — adapting to a layout change
- [ ] `parser:enhance` — improving the parser engine
- [ ] `schema:proposal` — schema change (requires RFC discussion first)
- [ ] `docs` — documentation only

## Summary

<!-- 1-3 sentences. What changed, why. -->

## For merchant / variant PRs

### Merchant
- **ID:** `de.<slug>`
- **Country:** DE / AT / CH
- **Parent chain:** (none) or `de.edeka`

### Sample evidence
- **Sample file(s):** `merchants/<country>/<merchant>/samples/<YYYY-MM-DD>-<location>.txt`
- **ZIP region:** ...
- **Pattern classes triggered:**
  - [ ] simple_item
  - [ ] quantity_item (inline / multiline)
  - [ ] weight_item
  - [ ] pfand_einweg / pfand_mehrweg / pfand_return / pfand_aggregate
  - [ ] discount / coupon
  - [ ] loyalty

### Anonymization checklist
- [ ] No full 16-digit card numbers
- [ ] No customer / loyalty IDs (PAYBACK, etc.)
- [ ] No cashier full names
- [ ] No emails (other than merchant's public email)
- [ ] No personal phone numbers

### Test evidence
- **Test fixture:** `merchants/<country>/<merchant>/tests/parse_test*.yaml`
- **Local pytest result:** All `N` tests pass ✅
- **Totals reconciliation:** grand_total matches computed_total ✅

## For parser / schema PRs

### Affected merchants
<!-- Which merchant tests might be impacted? -->
- [ ] de.dm — pytest pass
- [ ] de.knolles-markt — pytest pass
- [ ] de.lidl — pytest pass
- [ ] de.rewe — pytest pass

### Backward compatibility
- [ ] No existing test fails
- [ ] Schema version bumped if needed
- [ ] Migration documented if breaking

## Reviewer focus

<!-- What should the reviewer pay particular attention to? -->

---

🤖 If this PR was prepared with AI assistance: please confirm
- [ ] You read the resulting changes yourself
- [ ] You ran `pytest` locally and it passed
- [ ] You verified the sample receipt parses correctly with `forager-parser parse`
