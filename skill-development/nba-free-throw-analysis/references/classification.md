# Classification Reference

## Precedence

Classify structured free-throw sequence text first, nearby foul/play text second, and inference last. Reuse the first attempt's trip type for later attempts in that trip.

## Trip types

- `and-one`: one-shot award linked to a made field goal and shooting foul
- `shooting`: ordinary two- or three-shot shooting award
- `technical`: technical-foul award
- `defensive-three-seconds`
- `transition-take`
- `clear-path`
- `flagrant`
- `away-from-play`
- `other`: evidence is insufficient for a supported type

## Interruption labels

Track timeout, replay/challenge, and substitution independently. `interrupted` is true when any intervening administrative event exists. Use wall-clock timestamps for elapsed-time fields; game clock cannot measure a dead-ball wait.

Count only events between the initiating foul/play and the attempt. Parse clocks such as `39.1` as seconds remaining. Use play-array indexes, not ESPN `sequenceNumber`, to join attempts to substitution stints.

## Conditional splits

For `2 of 2`, report separate results after a made first attempt and a missed first attempt. Keep two-shot and three-shot conditional buckets separate. Always retain the trip ID so conditions can be recomputed from the attempt CSV.

## Validation

For each game, compare classified attempts with the player's FTA in the game log or box score. A season is complete only when every eligible game downloads and reconciles. Technical free throws may omit `1 of 1`; treat an explicit `technical free throw` description as a high-confidence single attempt.

For team runs, reconcile each player's game FTA and the summed team FTA. Include every player with an official attempt, regardless of final-roster status. Flag missing workload joins separately from free-throw classification.
