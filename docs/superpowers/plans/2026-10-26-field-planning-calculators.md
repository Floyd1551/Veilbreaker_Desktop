# Field planning calculators — implementation plan

**Scope:** Add MTU/MSS, TCP bandwidth-delay product, fiber optical budget, and PoE source budget to the existing offline Tools search and calculator host. These are calculated planning estimates, never captured evidence.

**Architecture:** Keep RF formulas in `rf_tools.py`. Put the four new formulas and metadata in `engineering_tools.py`, combine calculator metadata and dispatch in `field_tools.py`, and use that combined catalog from `tool_registry.py` and the existing calculator UI. Add native schematic diagrams for fiber and PoE that derive labels and values from the calculation snapshot.

**Validation:** Write failing tests for each formula, units, invalid/cross-field input, exact search category/routing, snapshot export, and diagram consistency before implementation. Run focused tests, full suite, and seven-page GUI smoke. Check Tools at 1280×720 and a narrow view for horizontal overflow.

**Boundaries:** No standards compliance claim, live measurement, automatic evidence attachment, or equipment-library lookup. PoE budgets are source-side; cable drop and per-port PSE limits are explicitly excluded. Fiber budget uses operator-entered attenuation and losses and cannot establish physical route condition.
