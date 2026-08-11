# ux-dom membership contract

## `matches` — formal scope

**Scope set** for node `N`:

```text
faces(N) = { N } ∪ { N._entry }   # second only if Component with distinct _entry
```

**Evaluation:**

```text
N.matches(tag, **attrs)  ⇔  ∃ F ∈ faces(N) : query(F, tag) ∧ attrs_ok(F, attrs)
```

* No recursion into `F.children`.
* `query`: class → `isinstance`; str → type name; instance → `F is tag`;
  omitted tag → type check skipped (attrs only / bare `matches()`).
* `attrs_ok`: each kwarg after `clean_attribute`; `None` value = key present.

**Scope boundary:** anything not in `faces(N)` is invisible to `matches`,
including every child of a Component root.

```text
Card faces:  [Card instance]  [div#card-root]
             └─ matches sees only these two
                span#title, button  →  NOT in scope of Card.matches
```

## Three APIs

```text
                    faces(N)     descendants of faces
matches(X)          YES          NO
get(X)              YES          YES
X in N              YES          YES
bool(N)             always True (object exists)
len(N)              child count of N (Component: of _entry)
```

## Recipes

| Intent | API |
|--------|-----|
| Am I this class / root type? | `N.matches(div)` |
| Am I this exact instance (or my root)? | `N.matches(el)` |
| Is instance anywhere under me? | `el in N` / `N.get(el)` |
| Find all spans under me | `N.get(span)` |

## Anti-pattern

```python
card.matches(child)   # False for real children — out of matches scope
child in card         # True
card.get(child)       # [child]
```
