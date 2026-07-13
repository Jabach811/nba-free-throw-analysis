# NBA Free-Throw Classifier: Curry Pilot Design

## Objective

Build an auditable play-by-play pipeline that classifies every Stephen Curry free-throw attempt from the 2025-26 NBA regular season, Play-In, and playoffs. The pilot must preserve enough raw evidence and classification detail to scale the same process to every NBA player.

## Scope

The pilot includes all official 2025-26 games involving Curry in these segments:

- Regular season
- Play-In Tournament
- NBA playoffs

Preseason, exhibitions, and the All-Star Game are excluded. Only attempts officially credited to Stephen Curry are included.

## Data Strategy

Use official NBA game and play-by-play records as the primary source. Reconstruct free-throw trips locally rather than relying on a site's precomputed splits. Enhanced play-by-play tooling may assist with ingestion or normalization, but the resulting classifications must remain reproducible from stored source events.

Each game's extracted Curry attempt count must be reconciled with its official box score. Season-level totals must also reconcile with official totals for each competition segment. Source corrections and duplicated, rescinded, or reordered events must be retained and handled explicitly rather than silently discarded.

## Processing Model

The pipeline has four independent stages:

1. **Game discovery** finds every eligible Warriors game and records its season segment.
2. **Event ingestion** downloads and stores the original play-by-play and box-score evidence.
3. **Trip reconstruction** links attempts belonging to the same award and connects the trip to its initiating foul or made basket.
4. **Classification and reporting** assigns multi-label attributes, validates totals, and generates attempt-level and summary outputs.

Raw records and derived records remain separate. Reclassification must never require downloading the source again when the raw data is already cached.

## Attempt-Level Schema

Every Curry attempt records:

- Season, competition segment, game ID, date, opponent, venue, and game result
- Period, game clock, event order, Curry's team score, opponent score, and score margin before the attempt
- Made or missed result
- Attempt position and announced trip length: `1 of 1`, `1 of 2`, `2 of 2`, `1 of 3`, `2 of 3`, or `3 of 3`
- Reconstructed trip ID and initiating event ID
- Trip type: shooting foul, and-one, technical, defensive three seconds, transition take, clear path, flagrant, away-from-play, or other
- Previous attempt result within the trip, when applicable
- All intervening event types between the initiating event and attempt
- Whether a timeout, replay, coach's challenge, substitution, or other interruption occurred
- Immediate versus interrupted attempt
- Raw source description, source event IDs, and source URL or endpoint identity
- Classification confidence and anomaly notes

Labels are intentionally multi-valued. For example, an attempt may simultaneously be `1 of 1`, `and-one`, `post-timeout`, `post-review`, and `interrupted`.

## Trip Reconstruction Rules

Attempts with compatible shooter identity, period, game clock, sequence numbering, and nearby event order are grouped into a trip. Sequence labels are authoritative when internally consistent.

An and-one is linked to a preceding made two- or three-point field goal by Curry when the free throw is awarded from the associated shooting foul. A timeout, replay, challenge, substitution, or administrative event may occur between the basket and attempt without breaking that link.

A post-timeout attempt is any free throw with at least one timeout between its initiating event and the attempt. A delayed and-one is an and-one with at least one intervening event; delayed-and-one subcategories separately identify timeout, replay/challenge, substitution, and other interruption types.

Because standard play-by-play game clocks stop during dead balls, the pipeline will describe the interruption sequence but will not claim a real elapsed waiting time unless the source supplies trustworthy wall-clock timestamps.

## Required Summary Splits

For every category, report attempts, makes, misses, and percentage. The pilot summary includes:

- All free throws
- Every attempt position within one-, two-, and three-shot trips
- `2 of 2` after making the first
- `2 of 2` after missing the first
- `2 of 3` and `3 of 3`, conditional on all available prior results
- And-ones: all, immediate, interrupted, post-timeout, and post-review/challenge
- Technical and each other identifiable special free-throw type
- Post-timeout free throws across all trip types
- Regular season, Play-In, playoffs, and combined totals
- Quarter/overtime, score margin, clutch, home/road, opponent, and game-level splits where sample sizes permit

Percentages with zero attempts display as unavailable, not zero. Small samples always show their attempt count.

## Outputs

The pilot produces:

- An attempt-level CSV containing one row per Curry free throw
- A trip-level CSV containing one row per reconstructed trip
- A human-readable summary report with the required splits
- A validation report listing source-to-box-score reconciliation and every ambiguous or anomalous event
- A cached raw-data directory organized by game ID

## Error Handling and Confidence

The classifier must not guess silently. Clean sequence matches receive high confidence. Records requiring inference from neighboring events receive medium confidence with the rule recorded. Conflicting, missing, or unresolvable evidence receives low confidence and appears in the validation report for manual review.

Network failures are retryable and resumable. A failed game does not invalidate successfully cached games, but the combined report must be marked incomplete until every eligible game passes reconciliation.

## Verification

Automated tests will cover representative two-shot trips, conditional second attempts, three-shot trips, immediate and delayed and-ones, technicals, timeouts, reviews, substitutions, rescinded events, and malformed sequences.

The Curry pilot is accepted when:

1. Every eligible game is accounted for.
2. Attempt totals reconcile at game and competition-segment levels.
3. Every attempt has raw source evidence.
4. All low-confidence cases are surfaced rather than hidden.
5. Summary totals reproduce exactly from the attempt-level CSV.

## Scaling Boundary

Player identity is an input, not hard-coded logic. Game discovery, caching, reconstruction, classification, validation, and reporting remain reusable for a player, team, season, or league-wide run. The pilot will avoid player-specific exceptions unless documented as general correction rules.
