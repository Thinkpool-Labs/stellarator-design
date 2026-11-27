# Tasks

Afternoon-sized pieces. Each ends in a design file, a measured number, or a short written finding.
`SOLVING.md` explains why each is worth doing.

## Warm-up (no record expected)

1. Run `baselines/leaderboard_start.py geometrical`, score it with the checker, and confirm you get
   the leaderboard's score. Report your machine and how long the high-fidelity score took.
2. Run `baselines/polish.py` for an hour on one problem. Report the best low-fidelity merit, the
   high-fidelity score of the result, and how often low and high fidelity disagreed on feasibility.

## Records

3. **geometrical:** start from the record design and push its maximum elongation below 1.17297 while
   holding aspect ratio <= 4, triangularity <= -0.5 and iota/nfp >= 0.3 (each to 1e-2). First
   find which constraints are active at the record design (print its metrics): that is where the
   trade lies.
4. **simple_to_build:** raise L_gradB above 13.9116 with log10(QI) <= -4. Try more toroidal modes
   than the record uses (it has M = 14, N = 14).
5. **mhd_stable:** find one feasible design that the record front doesn't dominate. The front is
   thinnest where aspect ratio is small (high compactness): look there first.

## Tools the swarm needs

6. A low-fidelity surrogate trained on the released dataset (about 180,000 boundaries with metrics)
   that predicts feasibility for the geometrical constraints. Report its accuracy on a held-out set.
7. A near-axis (pyQSC or `constellaration.initial_guess.generate_nae`) seed generator for QI
   designs, and how many of its seeds reach feasibility for `simple_to_build` under polish.
8. A script that runs the high-fidelity scorer on many machines at once and records each result's
   time, so the expensive step is shared.

## Negative results are results

A method that fails after a day of work is worth a short entry: what you tried, the best number
you reached, how long it ran. Open an issue titled "attempt: <method>" with that and your script.
