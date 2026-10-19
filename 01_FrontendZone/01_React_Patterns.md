# React Patterns

*Guidelines for building maintainable, observable, and consistent frontend components.*

---

## 1️⃣ Philosophy

I structure React apps to **mirror platform flow**, ensuring:

- Components are modular and reusable  
- State management is predictable  
- UI is aligned with backend contracts  
- Observability and performance hooks are in place  
- Cross-layer consistency with backend and infrastructure  

---

## 2️⃣ Component Patterns

| Pattern | Purpose | Notes |
|---------|---------|-------|
| **Functional Components + Hooks** | Simpler, more predictable logic | Prefer over class components unless lifecycle hooks are critical |
| **Container / Presentational Split** | Separate data & UI | Container handles data; Presentational handles rendering |
| **Context for Global State** | Shared state management | Avoid prop-drilling; keep minimal context scopes |
| **Custom Hooks** | Encapsulate reusable logic | Examples: `useStockQuote`, `useFormValidation` |
| **Error Boundaries** | Catch UI errors gracefully | Wrap top-level components, log errors |

---

## 3️⃣ Data Flow

- Fetch data via services / APIs, not directly in UI  
- Use `useEffect` for side effects  
- Maintain deterministic state updates  
- Log important events for observability  

---

## 4️⃣ Principle

I treat React components as **flow participants**: they consume data, emit events, and report observability signals without breaking the platform consistency.
