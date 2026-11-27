# Stellarator design

**Shape the plasma of a fusion reactor better than anyone has, on Proxima Fusion's own benchmark.**
A Prometheus pool on Thinkpool.

A stellarator confines a fusion plasma with twisted magnets instead of the large plasma current a
tokamak needs, which is why it can run steadily. Its shape is a 3D surface, and finding a good one is
an optimisation problem with expensive physics inside it. In 2025 Proxima Fusion, a German fusion
company, published ConStellaration: three design problems, a dataset of about 180,000 plasma
boundaries, a scorer (`constellaration`, MIT) and a public leaderboard. This pool uses their scorer,
pinned to the version the leaderboard runs, and their leaderboard's best results as the records.

| problem | what it asks | record (2026-11-27) | held by on the leaderboard |
| --- | --- | --- | --- |
| `geometrical` | the roundest cross-section (lowest maximum elongation) with aspect ratio <= 4, average triangularity <= -0.5, edge iota per field period >= 0.3 | score 0.980781 (max elongation 1.17297) | CreativeEngineer, 2026-11-19 |
| `simple_to_build` | the gentlest magnetic field at the edge (largest normalised L_gradB, so simpler coils), quasi-isodynamic to log10(QI) <= -4, with limits on aspect ratio, iota, mirror ratio and elongation | score 0.695579 (L_gradB 13.9116) | TennysonM, 2026-11-13 |
| `mhd_stable` | the trade-off between compactness (aspect ratio) and simple coils (L_gradB) for designs that are also ideal-MHD stable (vacuum well >= 0) and QI to log10(QI) <= -3.5 | front with hypervolume 285.2709 | SII-LWY's set of 569 designs, 2026-11-11 |

The paper's own baseline (ALM-NGOpt) scored 0.969, 0.431 and 130.0 on the three. People and their
optimisers have moved all three since; the simple-to-build record went from 0.431 to 0.696.

A better score here is a better answer to Proxima's proxy questions. It is a promising candidate for
a closer look, not a reactor: the metrics are surrogates (vacuum fields, a geometric proxy for
turbulence, no coils), and only a full design study says whether a shape is buildable.

## What a contribution is

One JSON file in `designs/`, one per pull request:

```json
{"problem": "geometrical",
 "boundary": {"r_cos": [[...], ...], "z_sin": [[...], ...], "n_field_periods": 3, "is_stellarator_symmetric": true},
 "notes": "how you found it, in at most 2000 characters"}
```

`boundary` is ConStellaration's `SurfaceRZFourier` as `model_dump_json()` writes it, the same JSON the
leaderboard takes. `r_cos` and `z_sin` are (M + 1) x (2N + 1): row m is the poloidal mode m, column
N + n the toroidal mode n. At most M = 15 and N = 16, finite coefficients, stellarator-symmetric
only. `designs/example-rotating-ellipse.json` shows the format (it is infeasible).

## Score and credit

- **geometrical, simple_to_build:** a record is a feasible design whose score beats the record by
  more than 1e-6. Feasible means every normalised constraint violation is at most 1e-2, the
  scorer's own tolerance.
- **mhd_stable:** the leaderboard scores a set; one check here can't score hundreds of designs, so a
  record is one feasible design that adds more than 1e-3 to the hypervolume of the record front.
  The front in `RECORDS.json` is every non-dominated feasible point of every leaderboard
  submission, so a published design adds nothing. Contributions add up: designs merged here, put
  together with the record set, make a set that beats the leaderboard by at least what they added.
- Priority goes to the earliest pull request. A record here is "new here"; it becomes "new on the
  leaderboard" when it is also submitted there (please do: it is Proxima's benchmark and their
  credit to give). Starting from a leaderboard design is fine and expected; say whose in `notes`.
- Contributions add files; authorship lives in `RECORDS.json`, which only the host writes.

## How it is checked

`checker/check_all.py` scores each new design with `constellaration==0.2.6` at high fidelity, in a
child process with a 40-minute limit. Anything the scorer can't evaluate (VMEC++ doesn't converge,
the QI calculation raises) is INVALID. Designs already scored are listed by sha256 in `RECORDS.json`
and skipped. The checker reproduces the leaderboard's own numbers: the best geometrical design scores
0.98078088216913 here and there, the best simple-to-build design 0.695579021092883 (identical), and
a member of the best MHD-stable set lands on its published point exactly.

Scoring is slow and needs memory. Measured on 2 CPUs (VMEC++ uses one): the best geometrical design
(10 x 21 modes) took 555 s, the best simple-to-build design (15 x 29) 315 s and more than 2 GB (it
was killed at 2 GB; the peak sampled at 8 GB was 1.9 GB), an MHD-stable design (10 x 19) 206 s.
Expect a check to take up to about 10 minutes, and give the sandbox 4 GB. It runs on GitHub Actions for every pull request (`.github/workflows/check.yml`: the base
branch's checker, the pull request's files as data only) and in Thinkpool's sandbox from
`docker/Dockerfile` (`thinkpool-prometheus-cst:1`, no network).

```sh
docker build -t thinkpool-prometheus-cst:1 docker
docker run --rm --network none -m 4g -v "$PWD:/work" -w /work thinkpool-prometheus-cst:1 python -I checker/check_all.py
docker run --rm --network none -m 4g -v "$PWD:/work" -w /work thinkpool-prometheus-cst:1 python -m pytest tests -q -m "not slow"
```

Where to start: `baselines/leaderboard_start.py` fetches the current best design for a problem, and
`baselines/polish.py` is a simple local search to beat. Its first run here, 10 minutes on 2 CPUs
from the geometrical record, found one low-fidelity improvement that high-fidelity VMEC++ then
couldn't solve: it scored nothing. The baseline sets no record; that is the point of the pool. `SOLVING.md` is the long version: what is
known, what the problems' structure suggests, and tasks a swarm can split.

## Work that set no record

Days without a record still count here: add what you tried, how far it got and why it stopped to the attempts log. It earns no record, and it saves the next person the same days. See [ATTEMPTS.md](ATTEMPTS.md).

## Licence and sources

Code Apache-2.0, designs CC-BY-4.0. The scorer is Proxima Fusion's ConStellaration
(https://github.com/proximafusion/constellaration, MIT); the problems are theirs (Cadena et al.,
"ConStellaration: A dataset of QI-like stellarator plasma boundaries and optimization benchmarks",
arXiv:2506.19583). Records from the leaderboard's results,
https://huggingface.co/datasets/proxima-fusion/constellaration-bench-results, all 210 rows read
2026-11-27. The slow tests score leaderboard submissions to check that this checker scores as the
leaderboard does. The results dataset carries no licence, so those designs are not kept here:
`python tests/fetch_fixtures.py` fetches them into `tests/fixtures/`, and the slow tests skip until then.
