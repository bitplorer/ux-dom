------------------------- MODULE WebSocketIsolation -------------------------
EXTENDS Naturals, FiniteSets, Integers, TLC
CONSTANTS Conns, MaxVal
ASSUME MaxVal \in Nat /\ MaxVal >= 1
Absent == -1
VARIABLES inst, live
vars == <<inst, live>>
TypeOK ==
  /\ inst \in [Conns -> (Nat \cup {Absent})]
  /\ live \subseteq Conns
  /\ \A c \in Conns : (c \in live) <=> (inst[c] # Absent)
Init ==
  /\ inst = [c \in Conns |-> Absent]
  /\ live = {}
Connect(c) ==
  /\ c \notin live
  /\ inst' = [inst EXCEPT ![c] = 0]
  /\ live' = live \union {c}
Bump(c) ==
  /\ c \in live
  /\ inst[c] < MaxVal
  /\ inst' = [inst EXCEPT ![c] = @ + 1]
  /\ UNCHANGED live
Release(c) ==
  /\ c \in live
  /\ inst' = [inst EXCEPT ![c] = Absent]
  /\ live' = live \ {c}
Next ==
  \/ \E c \in Conns : Connect(c)
  \/ \E c \in Conns : Bump(c)
  \/ \E c \in Conns : Release(c)
Stutter == UNCHANGED vars
Spec == Init /\ [][Next \/ Stutter]_vars
ReleasedAreAbsent == \A c \in Conns : c \notin live => inst[c] = Absent
LiveArePresent == \A c \in Conns : c \in live => inst[c] \in 0..MaxVal
IsolationOK == TypeOK /\ ReleasedAreAbsent /\ LiveArePresent
====
