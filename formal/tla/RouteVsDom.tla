----------------------------- MODULE RouteVsDom -----------------------------
EXTENDS Naturals, FiniteSets, TLC
CONSTANTS MaxChildren, MaxRoutes
VARIABLES exists, children, routeHits
vars == <<exists, children, routeHits>>
TypeOK ==
  /\ exists \in BOOLEAN
  /\ children \in 0..MaxChildren
  /\ routeHits \in 0..MaxRoutes
Init ==
  /\ exists = FALSE
  /\ children = 0
  /\ routeHits = 0
RouteGet ==
  /\ routeHits < MaxRoutes
  /\ exists' = TRUE
  /\ children' = 1
  /\ routeHits' = routeHits + 1
RouteAdd ==
  /\ routeHits < MaxRoutes
  /\ exists' = TRUE
  /\ children' = 1
  /\ routeHits' = routeHits + 1
DomGet ==
  /\ exists = TRUE
  /\ UNCHANGED vars
DomAdd ==
  /\ exists = TRUE
  /\ children < MaxChildren
  /\ children' = children + 1
  /\ UNCHANGED <<exists, routeHits>>
DomClear ==
  /\ exists = TRUE
  /\ children' = 0
  /\ UNCHANGED <<exists, routeHits>>
Next == RouteGet \/ RouteAdd \/ DomGet \/ DomAdd \/ DomClear
Stutter == UNCHANGED vars
Spec == Init /\ [][Next \/ Stutter]_vars
RouteDoesNotBlockDom == exists => children \in 0..MaxChildren
====
