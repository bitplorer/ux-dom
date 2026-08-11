------------------------- MODULE RenderIdempotent -------------------------
(***************************************************************************
 * After the tree is frozen (first render), further renders are equal.
 * Control flags are sticky (Render does not clear openTag).
 ***************************************************************************)
EXTENDS Naturals, Sequences, TLC
CONSTANTS MaxRenders
VARIABLES openTag, body, lastOut, renders, everRendered
vars == <<openTag, body, lastOut, renders, everRendered>>
Out == <<openTag, body>>
TypeOK ==
  /\ openTag \in {0, 1}
  /\ body \in {0, 1}
  /\ renders \in 0..MaxRenders
  /\ everRendered \in BOOLEAN
  /\ lastOut \in {0, 1} \X {0, 1}
Init ==
  /\ openTag = 0
  /\ body = 1
  /\ lastOut = <<0, 1>>
  /\ renders = 0
  /\ everRendered = FALSE
\* Mutations only before first render (build phase)
SetOpenTag ==
  /\ ~everRendered
  /\ openTag' = 1
  /\ UNCHANGED <<body, lastOut, renders, everRendered>>
FlipBody ==
  /\ ~everRendered
  /\ body' = IF body = 0 THEN 1 ELSE 0
  /\ UNCHANGED <<openTag, lastOut, renders, everRendered>>
Render ==
  /\ renders < MaxRenders
  /\ lastOut' = Out
  /\ renders' = renders + 1
  /\ everRendered' = TRUE
  /\ UNCHANGED <<openTag, body>>
Next == SetOpenTag \/ FlipBody \/ Render
Stutter == UNCHANGED vars
Spec == Init /\ [][Next \/ Stutter]_vars
\* After first render, every render result equals current frozen Out
Idempotent ==
  everRendered => lastOut = <<openTag, body>>
====
