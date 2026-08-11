------------------------------ MODULE UniqueId ------------------------------
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS MaxTime, MaxSeed, MaxIds

ASSUME MaxTime \in Nat /\ MaxSeed \in Nat /\ MaxIds \in Nat
ASSUME MaxSeed >= 2 /\ MaxTime >= 1

VARIABLES time, oldTime, seed, issued, count, atTick

vars == <<time, oldTime, seed, issued, count, atTick>>

IdOf(t, s) == t * (MaxSeed + 1) + s

TypeOK ==
  /\ time \in 0..MaxTime
  /\ oldTime \in 0..MaxTime
  /\ seed \in 1..MaxSeed
  /\ issued \subseteq Nat
  /\ count \in 0..MaxIds
  /\ atTick \in 0..MaxSeed

Init ==
  /\ time = 1
  /\ oldTime = 0
  /\ seed = 1
  /\ issued = {}
  /\ count = 0
  /\ atTick = 0

Tick ==
  /\ count < MaxIds
  /\ time < MaxTime
  /\ time' = time + 1
  /\ UNCHANGED <<oldTime, seed, issued, count, atTick>>

NextId ==
  /\ count < MaxIds
  /\ LET same == (time <= oldTime)
         s2 == IF same
               THEN IF seed < MaxSeed THEN seed + 1 ELSE seed
               ELSE seed
         id == IdOf(time, s2)
         at == IF same THEN atTick + 1 ELSE 1
     IN  /\ at <= MaxSeed
         /\ (~same \/ seed < MaxSeed)
         /\ seed' = s2
         /\ oldTime' = time
         /\ issued' = issued \union {id}
         /\ count' = count + 1
         /\ atTick' = at
  /\ UNCHANGED time

\* Allow graceful stop (avoids TLC "deadlock" at bound)
Done ==
  /\ count = MaxIds \/ (time = MaxTime /\ ~(seed < MaxSeed \/ time > oldTime) = FALSE)
  /\ UNCHANGED vars

\* Simpler Done: always allow stutter at any state (TLC deadlock off)
Stutter == UNCHANGED vars

Next == Tick \/ NextId
Spec == Init /\ [][Next \/ Stutter]_vars

Unique == Cardinality(issued) = count
====
