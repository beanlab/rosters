# Practical Habits for Pragmatic Engineering and Software Craftsmanship

Absolutely — here are concrete habits that combine **pragmatic engineering** and **software craftsmanship**.

## Habits that embody both

### 1. Start with the smallest useful version
- Build the simplest thing that solves the real problem.
- Keep the code clean enough that it won’t become a burden.
- Don’t overdesign, but don’t hack blindly either.

**Practice:** before writing code, ask:  
“What's the minimum solution that works and won’t embarrass me later?”

---

### 2. Write code for the next human
- Optimize for readability first.
- Use clear names, small functions, and straightforward control flow.
- Future maintainers matter more than cleverness.

**Practice:** if a teammate would need a long explanation, improve the code or add a comment.

---

### 3. Add tests where they buy down real risk
- Don’t test everything mechanically.
- Test important behavior, edge cases, and fragile logic.
- Use tests to support confident change, not as a ritual.

**Practice:** ask:  
“Would this test catch a likely regression or protect a tricky invariant?”

---

### 4. Refactor continuously, in small steps
- Don’t wait for a “big cleanup” that never comes.
- Improve structure as you learn more.
- Keep code healthy while shipping features.

**Practice:** whenever you touch a messy area, leave it a little better than you found it.

---

### 5. Prefer explicit decisions over accidental complexity
- Make conventions and boundaries clear.
- Remove ambiguity from APIs, configs, and flow.
- Use standard patterns when they reduce cognitive load.

**Practice:** if a design requires a lot of explanation, see if the structure can be made more obvious.

---

### 6. Measure before optimizing
- Don’t guess at bottlenecks.
- Let data guide performance work.
- When optimization is needed, do it carefully and document the tradeoff.

**Practice:** ask:  
“What evidence do we have that this is a problem?”

---

### 7. Use craftsmanship to support pragmatism
- Good craftsmanship makes pragmatic delivery faster over time.
- Clean code, good tests, and good tooling reduce future friction.

**Practice:** invest in quality where it repeatedly pays off, not where it just feels elegant.

---

### 8. Be willing to ship imperfectly, but not carelessly
- Shipping is important.
- But ship with guardrails: tests, logging, rollback plan, and known scope.

**Practice:** aim for “safe enough to learn from” rather than “perfect.”

---

### 9. Keep technical debt visible and intentional
- Some debt is acceptable if it helps deliver value now.
- But know what you’re taking on and why.
- Don’t let debt become invisible and chronic.

**Practice:** when you cut a corner, record it briefly and decide whether it needs follow-up.

---

### 10. Review code for impact, not just style
- Ask whether the solution is correct, maintainable, and appropriately simple.
- Avoid bikeshedding.
- Focus on user value, reliability, and future cost.

**Practice:** in reviews, ask:
- Is this the right level of complexity?
- Is this easy to change later?
- What could break in production?

---

### 11. Improve communication as part of the craft
- Pragmatism needs alignment.
- Craftsmanship includes explaining tradeoffs clearly.

**Practice:** write short design notes or comments when a decision is non-obvious.

---

### 12. Treat “done” as useful, not merely finished
- A task is done when it delivers value and can be maintained.
- Avoid leaving behind fragile or opaque code just because it compiles.

**Practice:** before closing work, check:
- Does it solve the intended problem?
- Is it understandable?
- Is it safe to operate?

---

## A simple rule of thumb

A strong combined mindset is:

> **Build the simplest thing that works, make it clear enough to live with, and improve it as reality teaches you more.**
