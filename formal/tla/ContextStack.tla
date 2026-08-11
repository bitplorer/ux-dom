---------------------------- MODULE ContextStack ----------------------------
(***************************************************************************
 * UxDom concurrent context-manager stack (dom_tag with / async with).
 *
 * Each worker key (thread × task × greenlet) owns an independent stack.
 * Enter pushes; Exit pops; Abort clears; Render freezes stacks.
 ***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS Workers, Nodes, MaxDepth
ASSUME MaxDepth \in Nat /\ MaxDepth >= 1

VARIABLES stack, owner, phase
vars == <<stack, owner, phase>>

TypeOK ==
  /\ stack \in [Workers -> Seq(Nodes)]
  /\ owner \in [Nodes -> SUBSET Workers]
  /\ phase \in {"build", "render"}

Init ==
  /\ stack = [w \in Workers |-> << >>]
  /\ owner = [n \in Nodes |-> {}]
  /\ phase = "build"

Free(n) == owner[n] = {}

Enter(w, n) ==
  /\ phase = "build"
  /\ Len(stack[w]) < MaxDepth
  /\ Free(n)
  /\ stack' = [stack EXCEPT ![w] = Append(stack[w], n)]
  /\ owner' = [owner EXCEPT ![n] = @ \union {w}]
  /\ UNCHANGED phase

Exit(w) ==
  /\ phase = "build"
  /\ Len(stack[w]) > 0
  /\ LET n == stack[w][Len(stack[w])]
     IN /\ stack' = [stack EXCEPT ![w] = SubSeq(stack[w], 1, Len(stack[w]) - 1)]
        /\ owner' = [owner EXCEPT ![n] = @ \ {w}]
  /\ UNCHANGED phase

Abort(w) ==
  /\ phase = "build"
  /\ Len(stack[w]) > 0
  /\ LET held == { stack[w][i] : i \in 1..Len(stack[w]) }
     IN /\ stack' = [stack EXCEPT ![w] = << >>]
        /\ owner' = [n \in Nodes |->
             IF n \in held THEN owner[n] \ {w} ELSE owner[n]]
  /\ UNCHANGED phase

StartRender ==
  /\ phase = "build"
  /\ phase' = "render"
  /\ UNCHANGED <<stack, owner>>

EndRender ==
  /\ phase = "render"
  /\ phase' = "build"
  /\ UNCHANGED <<stack, owner>>

Next ==
  \/ \E w \in Workers, n \in Nodes : Enter(w, n)
  \/ \E w \in Workers : Exit(w)
  \/ \E w \in Workers : Abort(w)
  \/ StartRender
  \/ EndRender

Stutter == UNCHANGED vars
Spec == Init /\ [][Next \/ Stutter]_vars

AtMostOneOwner ==
  \A n \in Nodes : Cardinality(owner[n]) <= 1

OwnerMatchesStack ==
  \A n \in Nodes :
    owner[n] = { w \in Workers :
      \E i \in 1..Len(stack[w]) : stack[w][i] = n }

DistinctTops ==
  \A w1, w2 \in Workers :
    (w1 # w2 /\ Len(stack[w1]) > 0 /\ Len(stack[w2]) > 0)
      => stack[w1][Len(stack[w1])] # stack[w2][Len(stack[w2])]

Safe ==
  /\ TypeOK
  /\ AtMostOneOwner
  /\ OwnerMatchesStack

====
