# Quick Code Quality First-Pass Checklist

These questions are intended for a first pass over the code itself. They flag visible signals; a signal is not automatically a quality verdict.

## Readability and naming

- [ ] Can I follow what this function is doing on a first read? — **Readability**
- [ ] Is the function’s purpose apparent from its code and name? — **Clarity**
- [ ] Do the names tell me what the variables, functions, and classes represent? — **Naming quality**
- [ ] Do nearby names or code patterns use noticeably inconsistent conventions? — **Consistency; inconsistent naming code smell**

## Function and class size

- [ ] Is a function unusually long or visibly handling many steps? — **Long function code smell**
- [ ] Does a class have many methods or fields? — **Large class code smell**
- [ ] Does a function take many separate arguments? — **Long parameter list code smell**

## Control flow and complexity

- [ ] Are conditionals or loops nested several levels deep? — **Excessive nesting code smell**
- [ ] Does a condition combine many clauses or levels of `and` / `or`? — **Complex conditional code smell**
- [ ] Does a boolean argument make the function take substantially different paths? — **Flag argument code smell**
- [ ] Does an expression navigate through a long chain, such as `a.b.c.d`? — **Message chain code smell**

## Duplication and unexplained values

- [ ] Do I see the same or very similar code repeated nearby? — **Duplicated code smell**
- [ ] Do I see unexplained literal numbers or strings in the logic? — **Magic number or string code smell**
- [ ] Do similar conditional branches appear more than once in this file? — **Repeated conditionals or switches code smell**

## Inputs, errors, and reporting

- [ ] Does the code visibly catch and report errors? — **Error handling**
- [ ] Does it catch every exception or silently ignore errors? — **Broad exception handling code smell**
