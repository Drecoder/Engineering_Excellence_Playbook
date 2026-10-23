# Frontend Clean Code Checklist

*Ensuring maintainable, readable, and consistent React code.*

---

## 1️⃣ Philosophy

I write code that is **predictable, testable, and observable**, aligning with backend and infra flow.

---

## 2️⃣ Checklist

| Area | Standard |
|------|---------|
| **Naming** | Descriptive, consistent, camelCase for variables and functions |
| **Components** | Small, focused, single responsibility |
| **Hooks** | Custom hooks reusable and decoupled |
| **State** | Minimal, predictable, immutable when possible |
| **Error Handling** | Use try/catch, error boundaries, and logging |
| **Styling** | Consistent CSS / Tailwind / CSS-in-JS conventions |
| **Testing** | Unit tests for logic; integration tests for data flow |
| **Observability** | Log key events; expose metrics where needed |
| **Documentation** | Component usage, props, context expectations |
| **Code Review** | Peer-reviewed PRs, adhere to lint rules |
| **Accessibility** | WCAG 2.2 AA: images have alt text, actions are buttons, every click handler works from the keyboard, labels are tied to their controls; checked by eslint-plugin-jsx-a11y (React) and angular-eslint template rules (Angular) as `AP-REACT-005`–`008` and `AP-ANGULAR-004`–`006` |

---

## 3️⃣ Principle

Clean code is **not about perfection**, it’s about **predictable behavior, flow observability, and maintainable evolution**.
