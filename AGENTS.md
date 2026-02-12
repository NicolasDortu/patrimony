## Coding Guidelines for Patrimony Agents

### Clean Code & SOLID Principles
- **Write clean, readable, and maintainable code.**
- **Follow the SOLID principles:**
	- **S**ingle Responsibility: Each module/class should have one responsibility.
	- **O**pen/Closed: Code should be open for extension, closed for modification.
	- **L**iskov Substitution: Subtypes must be substitutable for their base types.
	- **I**nterface Segregation: Prefer small, specific interfaces over large, general ones.
	- **D**ependency Inversion: Depend on abstractions, not concretions.

### Clean Architecture
- **Separate concerns**: Use clear boundaries between domain, application, infrastructure, and interface layers.
- **Dependency Rule**: Inner layers (domain, use cases) must not depend on outer layers (infrastructure, UI).
- **Keep business logic independent** from frameworks and external libraries.
- **Use dependency injection** to decouple components.

### Conciseness & Redundancy
- **Keep code as short and concise as possible.**
- **Avoid redundancy**: Do not repeat logic, comments, or code blocks.
- **Prefer composition over inheritance** where possible.
- **Use meaningful names** for variables, functions, and classes.

### Reflex Library & Project Purpose
- This project leverages the **Reflex** library to build a modern, interactive wealth tracking application.
- Use Reflex idioms and best practices for UI and state management.
- Ensure all UI code is modular, reusable, and testable.

### Additional Instructions
- **Write tests** for all business logic and critical features.
- **Document public APIs and modules** with concise docstrings.
- **Review and refactor code regularly** to maintain quality.
- **Prioritize security and data privacy** in all implementations.
- **Collaborate and communicate** clearly in code reviews and documentation.

---
