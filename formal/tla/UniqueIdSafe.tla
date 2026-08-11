---------------------------- MODULE UniqueIdSafe ----------------------------
EXTENDS Naturals, FiniteSets, TLC
CONSTANTS MaxTime, MaxSeed, MaxIds
VARIABLES time, oldTime, seed, issued, count
vars == <<time, oldTime, seed, issued, count>>
IdOf(t, s) == t * (MaxSeed + 1) + s
TypeOK ==
  /\ time \in 0..MaxTime /\ oldTime \in 0..MaxTime
  /\ seed \in 1..MaxSeed /\ issued \subseteq Nat /\ count \in 0..MaxIds
Init == time = 0 /\ oldTime = 0 /\ seed = 1 /\ issued = {} /\ count = 0
Tick == /\ count < MaxIds /\ time < MaxTime /\ time' = time + 1
        /\ UNCHANGED <<oldTime, seed, issued, count>>
NextId ==
  /\ count < MaxIds
  /\ LET same == (time <= oldTime)
         s1 == IF same THEN IF seed >= MaxSeed THEN 1 ELSE seed + 1 ELSE seed
         id == IdOf(time, s1)
     IN /\ id \notin issued
        /\ seed' = s1 /\ oldTime' = time
        /\ issued' = issued \union {id} /\ count' = count + 1
  /\ UNCHANGED time
Stutter == UNCHANGED vars
Next == Tick \/ NextId
Spec == Init /\ [][Next \/ Stutter]_vars
Unique == Cardinality(issued) = count
====
