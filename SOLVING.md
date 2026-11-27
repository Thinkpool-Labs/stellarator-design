# How to attack this, and how a swarm could split it

Written 2026-11-27 for the first contributors. What is known, what the problems' structure suggests,
and where the effort should go. None of this is a promise that a method works; the leaderboard is
the only judge, and this pool's check is the leaderboard's scorer.

## What the paper found (arXiv:2506.19583)

- The design variables are the boundary's Fourier coefficients: tens to a few hundred numbers
  (the records use 10 x 21 and 15 x 29 arrays). Every evaluation runs VMEC++, an ideal-MHD
  equilibrium solver, then (for the QI problems) a Boozer transform and a QI residual. Each is
  seconds at low fidelity and minutes at high fidelity, and none gives gradients.
- Of the three optimisers the authors tried, only ALM-NGOpt reached feasibility: an augmented
  Lagrangian outer loop (multipliers and penalties on the constraints) around Nevergrad's NGOpt as
  the inner, gradient-free optimiser, in a trust region that shrinks, with steps scaled down for
  higher modes. scipy trust-constr and COBYQA stalled infeasible (Table 4: geometrical maximum
  elongation 1.27 at violation 0.0002 for ALM-NGOpt; COBYQA reached the same elongation at violation
  0.95).
- The MHD-stable problem was solved as a sequence of single-objective problems with an aspect-ratio
  cap A* in {6, 8, 10, 12}, giving four points of the front (Table 5).
- The released dataset (about 180,000 boundaries, metrics included) contains no boundary feasible
  for the geometrical or simple-to-build problems (checked here with the datasets server on
  2026-11-27: zero rows for either constraint set, even at the 1e-2 tolerance). It is a training
  set and a source of warm starts, not a source of answers.

Baselines then: 0.969, 0.431, 130.0. The leaderboard on 2026-11-27: 0.980781, 0.695579, 285.27. The
simple-to-build and MHD numbers more than doubled, so the problems were far from solved at
publication and may still be.

## The structure of each problem

**geometrical** (no QI, the cheapest). Minimise maximum elongation subject to A <= 4, mean
triangularity <= -0.5, edge iota/nfp >= 0.3. Low aspect ratio and strong negative triangularity
pull the cross-section away from circular, and rotational transform from shaping alone needs
elongation or torsion; the record sits where these meet. Score = 1 - (elongation - 1)/9, so the
record's 1.17297 leaves at most 0.019 of score. Gains now come in the sixth decimal (the top two
leaderboard entries differ by 2e-6). Expect small, real improvements, and treat each one as a test
of how close the leaderboard's best is to a local optimum.

**simple_to_build.** Maximise the minimum normalised field-gradient scale length L_gradB (score =
L_gradB / 20) subject to QI (log10 QI <= -4), A <= 10, iota/nfp >= 0.25, edge mirror ratio <= 0.2,
elongation <= 5. Larger aspect ratio is allowed and usually helps QI. The QI constraint is the hard
one: it is a residual from a Boozer-coordinate calculation, noisy at low fidelity, and the scorer
raises an error (`Minimum of B is at the boundary`) for many shapes far from QI. Record 13.91, so
there is room to 20 on the scale, though physics may cap it well below.

**mhd_stable.** Two objectives (maximise L_gradB, minimise A) with QI to -3.5, vacuum well >= 0
(MHD stability), flux compression in bad curvature <= 0.9 (a turbulence proxy), mirror ratio <= 0.25,
iota/nfp >= 0.25. The record set holds 569 designs, so the front is densely sampled; gains will come
from a region where it bends or thins, or from a design family nobody has tried.

## Strategies worth a day each

1. **Polish the record designs.** Start from the leaderboard's best (`baselines/leaderboard_start.py`)
   and run a careful local search: ALM-NGOpt with a small trust region, CMA-ES restricted to the
   higher modes, or the (1+1) search in `baselines/polish.py`. Cheap to start, small gains, and it
   tells us whether the top designs are local optima.
2. **Continuation in mode count.** Optimise with few modes (M, N <= 3), then add modes and continue.
   The paper's runner fixes the mode count; the records use 10 to 15 poloidal modes, which suggests
   resolution matters. Measure the best score as a function of (M, N).
3. **Low fidelity for search, high for confirmation.** Low-fidelity VMEC++ is many times faster.
   Measure how often it agrees with high fidelity on feasibility near the record (Task 2), and keep
   only candidates whose margin survives the difference. The first polish run here found the
   failure mode at once: a step low-fidelity VMEC++ accepted made high-fidelity VMEC++ fail to
   converge (`RuntimeError: VMEC++ did not converge`), so the design scored nothing.
4. **Near-axis initialisation for the QI problems.** `constellaration.initial_guess.generate_nae`
   (and pyQSC/pyQIC) build boundaries from a near-axis expansion that are QI to leading order by
   construction. Seeding from a sweep over its parameters (nfp, elongation, mirror ratio, iota) may
   start the search far closer to the QI constraint than a rotating ellipse does.
5. **Surrogates from the dataset.** Train a model on the 180,000 boundaries to predict each metric
   (or feasibility) from the coefficients, optimise on the surrogate, and spend the real scorer only
   on its best proposals. The paper also trains a generative model on the dataset
   (`constellaration.generative_model`); conditioning it on the constraints is an obvious next step.
6. **Exploit the constraint structure.** Several constraints are close to closed form in a few
   coefficients (aspect ratio, triangularity, elongation are pure geometry, no VMEC needed). Project
   each candidate onto the geometric constraints before calling VMEC, and spend the expensive calls
   only on iota, QI and the vacuum well.
7. **For mhd_stable, target the front's gaps.** Compute where the record front's hypervolume gains
   most from one new point (the largest empty rectangles under the staircase) and run a
   single-objective search with the aspect ratio capped there.

## What it costs

The check is cheap per design and slow in wall time: one high-fidelity score, 10 to 40 minutes on
one core. The search is not cheap: the paper's runs and the leaderboard's leaders used many cores
for hours or days. This pool's sandbox is only the judge. Searching happens on contributors' own
machines, so a swarm's advantage is many machines trying different ideas at once, and sharing what
failed so nobody repeats it.

## Splitting it

Each strategy above splits into tasks that end in a number: "score as a function of mode count
for the geometrical problem, M, N in 1..8", "agreement of low and high fidelity on 200 designs near
the record", "surrogate accuracy for the triangularity constraint". `TASKS.md` lists the first ones.
A failed attempt is still a result: say what was tried, how long, and the best number reached, so the
next person doesn't spend the same day.

## Honest limits

These are Proxima's proxy questions, chosen to be computable. A design that scores well is a
promising candidate, never a reactor: no coils were designed, the field is a vacuum field (stability is
judged by the vacuum magnetic well alone), transport is a geometric proxy, and the scorer
is one code at one resolution. We say "beats the ConStellaration record", never "solves fusion".
