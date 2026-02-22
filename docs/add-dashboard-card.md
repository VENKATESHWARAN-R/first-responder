# How to add a new dashboard card

1. Extend backend namespace summary payload in `backend/app/services/k8s.py` and API route if needed.
2. Update TypeScript rendering in `frontend/app/page.tsx` (or namespace detail page).
3. Style via global design tokens in `frontend/styles/globals.css` (do not add ad-hoc hardcoded theme colors).
4. Add/adjust tests for transformer logic in `backend/app/tests`.
