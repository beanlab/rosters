---
type: skill
description: This skill instructs how to write code. If you are going to write code, load this skill.
---

# Bottom-up Coding

**Goal**: write cleaner, self-documenting code.

## Process

When writing code, always write the higher-level functions **above** the functions they call. This is a deliberate deviation from the convention of defining functions before their call-sites. 

When defining the body of a function, keep the logic as simple, clear, and straightforward as possible. The code should read as close to pseudocode as possible. Delegate to other functions. These other functions don't exist yet, but they will. 

### Classes

When defining classes, always start with the public interface. As you fill in the bodies of these functions, imagine the private helpers and private members as you use them. Then implement the private helper functions. Lastly, implement `__init__` and set the private members. 

### Modules

When implementing a module, follow a similar pattern to classes. Implement the public API first, followed by the private helper methods. 

### Larger Applications

For larger applications, use a similar top-down approach. Start with the **root** of the application—the primary entry-point—imagining the components, classes, and methods that would make implementation of the root clear, clean, and straightforward.

Think about how the application will be run. Start your implementation there, with the entry-point file. Build out additional files as they are referenced in existing code. 

Then continue down the stack, implementing these dependency resources. Always write the usage site **before** you write the definition and implementation. 

### Imports

Put your imports at the **bottom** of the file. As you need imported dependencies, simply use the dependency. We'll import it (and implement it as needed) later.

### Code duplication

As you write, do not worry about code duplication. Simply implement each function with the logic it needs. At a later step, this duplication will be addressed.

## Other Guidance

- Use type hints.
- Begin every function with a simple docstring of what that function is supposed to accomplish. 

## Post-processing

**AFTER** you have written the file, review the for code duplication. Identify all blocks of logic that *should* stay consistent and extract that logic into a shared helper function.

Note that just because two blocks of code are identical, it doesn't mean the code is duplicated. Two separate elements of business logic may have the same implementation today, but may evolve separately tomorrow. Duplicate code is logic that **should** be identical to maintain the integrity of the business logic. This is the code that should be refactored into a shared function.

Then, after addressing duplicated code, move any `import` statements to the top of the file. 

