# Information Architecture & Product Areas

How product PRDs are organized into files, how to choose and name a product **AREA**, and the
rule for deciding whether new work is a **requirement** in an existing area or a **new area
file**. Agent-facing copy of [`docs/prd/README.md` §4](../../../../../../../docs/prd/README.md).

---

## 1. Two levels only

The IA mirrors the engineering side's flatness:

```
Area (file)  →  Requirements (governed PRD-{AREA}-{NN} items)
```

- **Area** = one product area or feature = one file `docs/prd/{area}.md`. The uppercased name is
  the `{AREA}` token in every requirement ID in that file.
- **Requirement** = one governed `PRD-{AREA}-{NN}` item in the file's *Requirements* section.

There is no third level. If a requirement seems to need sub-requirements with their own
acceptance criteria, that is a signal to split it into sibling requirements.

---

## 2. Organize by product AREA, not engineering subsystem

A product **AREA** is the unit a Product Owner reasons about and a user would name:

- `SEARCH`, `ONBOARDING`, `BILLING`, `NOTIFICATIONS`, `GOVERNANCE`.

This is **intentionally a different axis** from the engineering SUBSYSTEM used by specs:

- One product area is frequently realized by **several** subsystems.
- One subsystem may serve **several** product areas.

Do **not** force PRD areas to match spec subsystems. Organize PRDs by the product surface; record
the cross-mapping via the Linked Specs table (see
[`prd-to-spec-linkage.md`](prd-to-spec-linkage.md)).

> Example: the product area `PRD-SEARCH` may be realized by `SPEC-INTEGRATIONS` (the vector index
> adapter) and `SPEC-SESSIONS` (query session handling). Neither subsystem is "the search
> subsystem"; search is a *product* concept spanning them.

---

## 3. Add a requirement vs. add an area

### Default: add a requirement

Adding a `PRD-{AREA}-{NN}` item to an existing area file is the **common case**. Do this when the
new need fits an existing area's scope. Append a `#### {Title} {#PRD-{AREA}-{NN+1}}` requirement,
add acceptance criteria and a Linked Specs row.

### Add a new area file only when ALL of these hold

1. **Cohesive product surface.** The need forms a recognizable product area with a clear
   boundary — not a feature of an existing one.
2. **Separately owned / planned.** It can be prioritized, reviewed, and shipped on its own
   cadence.
3. **Several requirements' worth.** It will hold more than one or two requirements. A single need
   is a *requirement*, never an area.

If even one fails, prefer a requirement in the nearest existing area.

### Decision flow

```
New product need
        │
        ▼
Does an existing area's scope cover it? ──yes──▶ add a REQUIREMENT there
        │ no
        ▼
Cohesive, separately-planned surface with ≥3 requirements' worth? ──no──▶ add a REQUIREMENT
        │ yes                                                              to the nearest area
        ▼
   add a NEW AREA file docs/prd/{area}.md
```

---

## 4. Naming an area

- **Token:** UPPERCASE alpha, hyphens allowed — `SEARCH`, `MODEL-ROUTING`. Matches the `{AREA}`
  slot in [`README.md` §3](../../../../../../../docs/prd/README.md).
- **File name:** lowercase form of the token — `model-routing.md` ↔ `PRD-MODEL-ROUTING-01`.
- **Durability:** the token appears in every requirement ID **and in every spec that cites it**.
  Renaming it breaks those cross-standard links. Choose durable, user-recognizable names.
- **User-facing language:** prefer the word a user or PM would use (`SEARCH`) over an internal
  code name.

---

## 5. Every directory has an orienting index

`docs/prd/` is indexed by its `README.md`. Any new subdirectory (e.g. `research/`) carries its
own index that orients a reader: what lives here, the naming convention, where to go next — the
same rule the engineering side applies under `docs/specs/`.

---

## 6. Common mistakes

| Mistake | Fix |
|---------|-----|
| Creating an area per engineering subsystem | Organize by product surface; map to subsystems via Linked Specs. |
| One area file per requirement | Group related requirements into an area. |
| Naming an area after an internal code name | Use the user-facing product term. |
| Renaming an `{AREA}` token to tidy up | Don't — it breaks spec cross-references. Supersede instead. |
| Putting acceptance/metrics in the spec | Those are PRD sections; the spec stays a contract. |

---

## See also

- [`prd-to-spec-linkage.md`](prd-to-spec-linkage.md) — recording the AREA↔SUBSYSTEM mapping.
- [`prd-template.md`](prd-template.md) — the requirement structure within an area.
- [`docs/prd/README.md` §4](../../../../../../../docs/prd/README.md) — the authoritative IA rules.
