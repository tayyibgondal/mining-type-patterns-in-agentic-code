# Statistical results

## TypeScript

Corpus stage: **stage2**. 5,618 agent PRs, 5,665 human PRs, 940 repositories.

### RQ1 type patterns

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| expressiveness: volume per PR | Mann-Whitney U | 36.238 | 7.183 | 3.76e-214 *** | - | Cliff's delta 0.337 |
| expressiveness: distinct constructs per PR | Mann-Whitney U | 2.881 | 1.506 | 7.58e-194 *** | - | Cliff's delta 0.316 |
| expressiveness: per 100 changed lines | Mann-Whitney U | 6.049 | 14.286 | 1.65e-29 *** | - | Cliff's delta -0.122 |
| expressiveness: per 100 lines | Mann-Whitney U (repo-clustered) | 6.861 | 14.498 | 3.08e-19 *** | - | Cliff's delta -0.647 |
| expressiveness: usage profile (omnibus) | profile permutation (10,000x) | 2.920 | 7.427 | 0.0001 *** | - | Spearman rho 0.964 |
| safety: volume per PR | Mann-Whitney U | 18.390 | 1.487 | 0 *** | - | Cliff's delta 0.455 |
| safety: distinct constructs per PR | Mann-Whitney U | 1.416 | 0.452 | 0 *** | - | Cliff's delta 0.431 |
| safety: per 100 changed lines | Mann-Whitney U | 3.805 | 4.245 | 6.51e-180 *** | - | Cliff's delta 0.293 |
| safety: per 100 lines | Mann-Whitney U (repo-clustered) | 3.280 | 4.668 | 4.14e-06 *** | - | Cliff's delta -0.331 |
| safety: usage profile (omnibus) | profile permutation (10,000x) | 3.805 | 4.245 | 0.0184 * | - | Spearman rho 0.943 |
| generics [TS-C1] | Mann-Whitney U | 0.212 | 1.088 | 1.7e-27 *** | 4.67e-27 | Cliff's delta 0.083 |
| conditional types [TS-C2] | Mann-Whitney U | 0.017 | 0.106 | 0.805 ns | 0.805 | Cliff's delta -0.001 |
| infer [TS-C3] | Mann-Whitney U | 0.010 | 0.065 | 0.0393 * | 0.048 | Cliff's delta 0.004 |
| mapped types [TS-C4] | Mann-Whitney U | 0.011 | 0.124 | 9.95e-06 *** | 1.56e-05 | Cliff's delta 0.012 |
| key remapping [TS-C5] | Mann-Whitney U | 0.000 | 0.013 | 0.473 ns | 0.52 | Cliff's delta 0.000 |
| keyof [TS-C7] | Mann-Whitney U | 0.065 | 0.247 | 5.71e-36 *** | 2.09e-35 | Cliff's delta 0.058 |
| typeof (type position) [TS-C8] | Mann-Whitney U | 0.206 | 0.311 | 2.64e-120 *** | 1.45e-119 | Cliff's delta 0.142 |
| indexed access types [TS-C9] | Mann-Whitney U | 0.001 | 0.000 | 3.74e-06 *** | 6.85e-06 | Cliff's delta 0.005 |
| utility types [TS-C10] | Mann-Whitney U | 0.528 | 0.787 | 3.16e-130 *** | 3.47e-129 | Cliff's delta 0.197 |
| optional property [TS-C14] | Mann-Whitney U | 1.861 | 4.618 | 0.000155 *** | 0.000213 | Cliff's delta 0.038 |
| enum [TS-C15] | Mann-Whitney U | 0.007 | 0.068 | 9.9e-13 *** | 2.18e-12 | Cliff's delta 0.022 |
| unknown [TS-D1] | Mann-Whitney U | 0.241 | 0.568 | 1.14e-51 *** | 1.36e-51 | Cliff's delta 0.094 |
| satisfies [TS-D2] | Mann-Whitney U | 0.042 | 0.000 | 9.33e-77 *** | 1.4e-76 | Cliff's delta 0.059 |
| as const [TS-D3] | Mann-Whitney U | 0.123 | 0.114 | 4e-120 *** | 8e-120 | Cliff's delta 0.124 |
| readonly [TS-D4] | Mann-Whitney U | 0.343 | 0.504 | 6.51e-39 *** | 6.51e-39 | Cliff's delta 0.075 |
| optional chaining (?.) [TS-D6] | Mann-Whitney U | 2.264 | 2.429 | 1.21e-243 *** | 7.24e-243 | Cliff's delta 0.318 |
| nullish coalescing (??) [TS-D7] | Mann-Whitney U | 0.792 | 0.630 | 4.29e-202 *** | 1.29e-201 | Cliff's delta 0.231 |

### RQ2 escape hatches

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| HEADLINE any [TS-E1]: prevalence | Chi-square | 0.425 | 0.263 | 1.32e-72 *** | - | Cramer's V 0.170 |
| HEADLINE any [TS-E1]: per 100 changed lines | Mann-Whitney U | 1.159 | 2.263 | 6.81e-35 *** | - | Cliff's delta 0.113 |
| HEADLINE any [TS-E1]: per 100 lines | Mann-Whitney U (repo-clustered) | 1.603 | 3.731 | 6.39e-11 *** | - | Cliff's delta -0.465 |
| HEADLINE any [TS-E1]: additions per PR | Mann-Whitney U | 5.611 | 1.360 | 6.14e-105 *** | - | Cliff's delta 0.200 |
| HEADLINE any [TS-E1]: removals per PR | Mann-Whitney U | 2.827 | 0.735 | 6.27e-41 *** | - | Cliff's delta 0.103 |
| Tier A escape hatches: per 100 changed lines | Mann-Whitney U | 2.139 | 4.776 | 0.0941 ns | - | Cliff's delta 0.017 |
| Tier B escape hatches: per 100 changed lines | Mann-Whitney U | 0.021 | 0.049 | 6.05e-42 *** | - | Cliff's delta 0.051 |
| suppression directives: share of PRs containing one | Chi-square | 0.068 | 0.064 | 0.424 ns | - | Cramer's V 0.008 |
| escape hatches: usage profile (omnibus) | profile permutation (10,000x) | 2.160 | 4.824 | 0.0001 *** | - | Spearman rho 0.900 |
| any [TS-E1] | Mann-Whitney U | 1.159 | 2.263 | 6.81e-35 *** | 1.7e-34 | Cliff's delta 0.113 |
| type assertion [TS-E3] | Mann-Whitney U | 0.728 | 1.791 | 1.34e-29 *** | 2.07e-29 | Cliff's delta 0.104 |
| non-null assertion (!) [TS-E4] | Mann-Whitney U | 0.246 | 0.657 | 1.66e-29 *** | 2.07e-29 | Cliff's delta 0.077 |
| Function type [TS-E6] | Mann-Whitney U | 0.006 | 0.065 | 1.23e-05 *** | 1.23e-05 | Cliff's delta -0.010 |
| type predicate (x is T) [TS-E8] | Mann-Whitney U | 0.021 | 0.049 | 6.05e-42 *** | 3.02e-41 | Cliff's delta 0.051 |

### RQ3 acceptance

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| acceptance: merged share | Chi-square | 0.525 | 0.775 | 1.56e-170 *** | - | Cramer's V 0.262 |
| acceptance within agent PRs: with vs without a Tier A escape hatch | Chi-square | 0.517 | 0.540 | 0.104 ns | - | Cramer's V 0.022 |
| acceptance within human PRs: with vs without a Tier A escape hatch | Chi-square | 0.750 | 0.799 | 1.04e-05 *** | - | Cramer's V 0.059 |
| REPO-MATCHED acceptance: merged share (20 shared repos) | Chi-square | 0.345 | 0.797 | 4.85e-80 *** | - | Cramer's V 0.361 |
| acceptance: Claude_Code vs all humans | Chi-square | 0.678 | 0.775 | 0.000411 *** | - | Cramer's V 0.046 |
| acceptance: Copilot vs all humans | Chi-square | 0.430 | 0.775 | 4.34e-179 *** | - | Cramer's V 0.326 |
| acceptance: Cursor vs all humans | Chi-square | 0.535 | 0.775 | 1.48e-46 *** | - | Cramer's V 0.179 |
| acceptance: Devin vs all humans | Chi-square | 0.543 | 0.775 | 9.44e-68 *** | - | Cramer's V 0.207 |
| acceptance: OpenAI_Codex vs all humans | Chi-square | 0.623 | 0.775 | 2.02e-28 *** | - | Cramer's V 0.133 |

### Robustness

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| REPO-MATCHED any: per 100 changed lines (20 shared repos) | Mann-Whitney U | 1.106 | 1.926 | 4.06e-11 *** | - | Cliff's delta 0.165 |

## C#

Corpus stage: **stage2**. 1,917 agent PRs, 4,496 human PRs, 305 repositories.

### RQ1 type patterns

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| expressiveness: volume per PR | Mann-Whitney U | 6.846 | 3.165 | 0.00344 ** | - | Cliff's delta 0.044 |
| expressiveness: distinct constructs per PR | Mann-Whitney U | 0.764 | 0.680 | 0.0952 ns | - | Cliff's delta 0.024 |
| expressiveness: per 100 changed lines | Mann-Whitney U | 0.659 | 2.006 | 2.61e-25 *** | - | Cliff's delta -0.157 |
| expressiveness: per 100 lines | Mann-Whitney U (repo-clustered) | 0.606 | 2.236 | 6.59e-24 *** | - | Cliff's delta -0.728 |
| expressiveness: usage profile (omnibus) | profile permutation (10,000x) | 0.659 | 2.006 | 0.0001 *** | - | Spearman rho 1.000 |
| safety: volume per PR | Mann-Whitney U | 22.200 | 4.962 | 8.83e-199 *** | - | Cliff's delta 0.451 |
| safety: distinct constructs per PR | Mann-Whitney U | 1.514 | 0.614 | 2.35e-212 *** | - | Cliff's delta 0.457 |
| safety: per 100 changed lines | Mann-Whitney U | 4.241 | 4.348 | 7.43e-112 *** | - | Cliff's delta 0.338 |
| safety: per 100 lines | Mann-Whitney U (repo-clustered) | 3.510 | 3.185 | 0.691 ns | - | Cliff's delta -0.029 |
| safety: usage profile (omnibus) | profile permutation (10,000x) | 4.241 | 4.348 | 0.0012 ** | - | Spearman rho 0.600 |
| generics [CS-C1] | Mann-Whitney U | 0.057 | 0.212 | 2.46e-05 *** | 4.1e-05 | Cliff's delta 0.034 |
| variance [CS-C2] | Mann-Whitney U | 0.000 | 0.032 | 0.554 ns | 0.659 | Cliff's delta 0.001 |
| tuple [CS-C3] | Mann-Whitney U | 0.560 | 1.601 | 1.98e-14 *** | 9.91e-14 | Cliff's delta -0.114 |
| type alias [CS-C4] | Mann-Whitney U | 0.029 | 0.107 | 0.659 ns | 0.659 | Cliff's delta 0.003 |
| readonly / ref struct [CS-C5] | Mann-Whitney U | 0.013 | 0.055 | 3.97e-11 *** | 9.92e-11 | Cliff's delta 0.027 |
| #nullable enable [CS-D1] | Mann-Whitney U | 0.152 | 0.522 | 0.0252 * | 0.0252 | Cliff's delta 0.012 |
| nullable annotation (T?) [CS-D2] | Mann-Whitney U | 2.337 | 2.022 | 1.22e-126 *** | 6.11e-126 | Cliff's delta 0.307 |
| pattern type test (is T x) [CS-D3] | Mann-Whitney U | 1.101 | 1.497 | 6.77e-100 *** | 1.13e-99 | Cliff's delta 0.284 |
| record / init / required [CS-D4] | Mann-Whitney U | 0.484 | 0.051 | 1.3e-122 *** | 3.24e-122 | Cliff's delta 0.170 |
| generic constraint (where) [CS-D5] | Mann-Whitney U | 0.167 | 0.255 | 1.03e-20 *** | 1.28e-20 | Cliff's delta 0.082 |

### RQ2 escape hatches

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| HEADLINE dynamic [CS-E1]: prevalence | Chi-square | 0.011 | 0.022 | 0.00711 ** | - | Cramer's V 0.034 |
| HEADLINE dynamic [CS-E1]: per 100 changed lines | Mann-Whitney U | 0.006 | 0.143 | 0.00473 ** | - | Cliff's delta -0.010 |
| HEADLINE dynamic [CS-E1]: per 100 lines | Mann-Whitney U (repo-clustered) | 0.013 | 0.109 | 2.43e-09 *** | - | Cliff's delta -0.250 |
| HEADLINE dynamic [CS-E1]: additions per PR | Mann-Whitney U | 0.039 | 0.080 | 0.00526 ** | - | Cliff's delta -0.010 |
| HEADLINE dynamic [CS-E1]: removals per PR | Mann-Whitney U | 0.014 | 0.041 | 0.0912 ns | - | Cliff's delta -0.004 |
| HEADLINE null-forgiving (!) [CS-E2]: prevalence | Chi-square | 0.325 | 0.056 | 5.35e-180 *** | - | Cramer's V 0.357 |
| HEADLINE null-forgiving (!) [CS-E2]: per 100 changed lines | Mann-Whitney U | 0.642 | 0.319 | 1.47e-173 *** | - | Cliff's delta 0.264 |
| HEADLINE null-forgiving (!) [CS-E2]: per 100 lines | Mann-Whitney U (repo-clustered) | 0.520 | 0.200 | 7.1e-05 *** | - | Cliff's delta 0.258 |
| HEADLINE null-forgiving (!) [CS-E2]: additions per PR | Mann-Whitney U | 3.686 | 0.755 | 4.05e-184 *** | - | Cliff's delta 0.272 |
| HEADLINE null-forgiving (!) [CS-E2]: removals per PR | Mann-Whitney U | 1.928 | 0.091 | 1.26e-97 *** | - | Cliff's delta 0.150 |
| Tier A escape hatches: per 100 changed lines | Mann-Whitney U | 0.764 | 0.472 | 1.37e-204 *** | - | Cliff's delta 0.321 |
| Tier B escape hatches: per 100 changed lines | Mann-Whitney U | 1.012 | 3.440 | 3.69e-24 *** | - | Cliff's delta -0.152 |
| suppression directives: share of PRs containing one | Chi-square | 0.149 | 0.051 | 1.04e-39 *** | - | Cramer's V 0.165 |
| escape hatches: usage profile (omnibus) | profile permutation (10,000x) | 0.894 | 1.068 | 0.0001 *** | - | Spearman rho 0.500 |
| dynamic [CS-E1] | Mann-Whitney U | 0.006 | 0.143 | 0.00473 ** | 0.00789 | Cliff's delta -0.010 |
| null-forgiving (!) [CS-E2] | Mann-Whitney U | 0.642 | 0.319 | 1.47e-173 *** | 7.34e-173 | Cliff's delta 0.264 |
| unsafe [CS-E5] | Mann-Whitney U | 0.053 | 0.143 | 0.0136 * | 0.017 | Cliff's delta 0.011 |
| Unsafe.As / MemoryMarshal [CS-E6] | Mann-Whitney U | 0.069 | 0.010 | 2.04e-71 *** | 5.09e-71 | Cliff's delta 0.079 |
| as operator [CS-E8] | Mann-Whitney U | 0.124 | 0.453 | 0.919 ns | 0.919 | Cliff's delta -0.001 |

### RQ3 acceptance

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| acceptance: merged share | Chi-square | 0.623 | 0.777 | 7.32e-37 *** | - | Cramer's V 0.158 |
| acceptance within agent PRs: with vs without a Tier A escape hatch | Chi-square | 0.690 | 0.576 | 5.39e-07 *** | - | Cramer's V 0.114 |
| acceptance within human PRs: with vs without a Tier A escape hatch | Chi-square | 0.819 | 0.773 | 0.0494 * | - | Cramer's V 0.029 |
| REPO-MATCHED acceptance: merged share (19 shared repos) | Chi-square | 0.636 | 0.846 | 2.46e-23 *** | - | Cramer's V 0.215 |
| acceptance: Copilot vs all humans | Chi-square | 0.565 | 0.777 | 4.76e-52 *** | - | Cramer's V 0.199 |
| acceptance: OpenAI_Codex vs all humans | Chi-square | 0.759 | 0.777 | 0.358 ns | - | Cramer's V 0.013 |

### Robustness

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| REPO-MATCHED dynamic: per 100 changed lines (19 shared repos) | Mann-Whitney U | 0.003 | 0.012 | 0.246 ns | - | Cliff's delta 0.006 |
| REPO-MATCHED null-forgiving (!): per 100 changed lines (19 shared repos) | Mann-Whitney U | 0.301 | 0.484 | 0.00268 ** | - | Cliff's delta 0.052 |

## Rust

Corpus stage: **stage2**. 1,220 agent PRs, 7,832 human PRs, 297 repositories.

### RQ1 type patterns

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| expressiveness: volume per PR | Mann-Whitney U | 26.134 | 9.719 | 1.31e-32 *** | - | Cliff's delta 0.207 |
| expressiveness: distinct constructs per PR | Mann-Whitney U | 2.204 | 1.660 | 1.14e-14 *** | - | Cliff's delta 0.133 |
| expressiveness: per 100 changed lines | Mann-Whitney U | 6.505 | 8.735 | 0.116 ns | - | Cliff's delta -0.027 |
| expressiveness: per 100 lines | Mann-Whitney U (repo-clustered) | 6.570 | 8.107 | 1.03e-10 *** | - | Cliff's delta -0.481 |
| expressiveness: usage profile (omnibus) | profile permutation (10,000x) | 6.505 | 8.735 | 0.0005 *** | - | Spearman rho 0.709 |
| safety: volume per PR | Mann-Whitney U | 28.191 | 5.063 | 6.27e-92 *** | - | Cliff's delta 0.352 |
| safety: distinct constructs per PR | Mann-Whitney U | 1.389 | 0.906 | 1.24e-60 *** | - | Cliff's delta 0.276 |
| safety: per 100 changed lines | Mann-Whitney U | 5.810 | 5.796 | 2.07e-18 *** | - | Cliff's delta 0.152 |
| safety: per 100 lines | Mann-Whitney U (repo-clustered) | 6.186 | 5.977 | 0.0132 * | - | Cliff's delta -0.185 |
| safety: usage profile (omnibus) | profile permutation (10,000x) | 5.810 | 5.796 | 0.534 ns | - | Spearman rho 0.900 |
| generics [RS-C1] | Mann-Whitney U | 0.478 | 1.013 | 0.000136 *** | 0.000221 | Cliff's delta -0.049 |
| lifetimes [RS-C2] | Mann-Whitney U | 1.930 | 2.684 | 0.000167 *** | 0.000241 | Cliff's delta 0.052 |
| trait bound [RS-C3] | Mann-Whitney U | 0.245 | 0.272 | 0.536 ns | 0.536 | Cliff's delta -0.005 |
| where clause [RS-C4] | Mann-Whitney U | 0.000 | 0.043 | 0.00815 ** | 0.00883 | Cliff's delta -0.009 |
| impl Trait [RS-C5] | Mann-Whitney U | 0.156 | 0.261 | 2.4e-06 *** | 6.25e-06 | Cliff's delta 0.038 |
| dyn Trait [RS-C6] | Mann-Whitney U | 0.136 | 0.383 | 5.25e-05 *** | 0.000114 | Cliff's delta 0.035 |
| type alias [RS-C7] | Mann-Whitney U | 0.175 | 0.312 | 0.0028 ** | 0.00364 | Cliff's delta 0.029 |
| associated type [RS-C8] | Mann-Whitney U | 0.372 | 0.484 | 7.77e-10 *** | 3.96e-09 | Cliff's delta 0.058 |
| PhantomData [RS-C9] | Mann-Whitney U | 0.029 | 0.046 | 0.00332 ** | 0.00392 | Cliff's delta 0.012 |
| enum definition [RS-C10] | Mann-Whitney U | 0.098 | 0.143 | 9.13e-10 *** | 3.96e-09 | Cliff's delta 0.063 |
| trait definition [RS-C11] | Mann-Whitney U | 0.535 | 0.115 | 6.65e-05 *** | 0.000123 | Cliff's delta 0.029 |
| Send / Sync bound [RS-C12] | Mann-Whitney U | 0.128 | 0.355 | 2.31e-13 *** | 3e-12 | Cliff's delta 0.052 |
| Option / Result [RS-C13] | Mann-Whitney U | 2.222 | 2.624 | 1.65e-06 *** | 5.35e-06 | Cliff's delta 0.080 |
| ? operator [RS-D1] | Mann-Whitney U | 2.745 | 2.933 | 2.6e-20 *** | 3.25e-20 | Cliff's delta 0.146 |
| TryFrom / checked_* [RS-D2] | Mann-Whitney U | 0.162 | 0.198 | 1.63e-26 *** | 4.06e-26 | Cliff's delta 0.073 |
| safe Option/Result handling [RS-D3] | Mann-Whitney U | 2.747 | 2.632 | 5.37e-23 *** | 8.96e-23 | Cliff's delta 0.164 |
| #[expect] / forbid(unsafe_code) [RS-D4] | Mann-Whitney U | 0.105 | 0.022 | 3.27e-38 *** | 1.64e-37 | Cliff's delta 0.029 |
| // SAFETY: comment [RS-D5] | Mann-Whitney U | 0.051 | 0.011 | 3.06e-10 *** | 3.06e-10 | Cliff's delta 0.016 |

### RQ2 escape hatches

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| HEADLINE unsafe (any form) [RS-E1f]: prevalence | Chi-square | 0.089 | 0.083 | 0.563 ns | - | Cramer's V 0.006 |
| HEADLINE unsafe (any form) [RS-E1f]: per 100 changed lines | Mann-Whitney U | 0.212 | 0.480 | 0.78 ns | - | Cliff's delta 0.002 |
| HEADLINE unsafe (any form) [RS-E1f]: per 100 lines | Mann-Whitney U (repo-clustered) | 0.229 | 0.400 | 2.34e-10 *** | - | Cliff's delta -0.389 |
| HEADLINE unsafe (any form) [RS-E1f]: additions per PR | Mann-Whitney U | 0.949 | 0.395 | 0.455 ns | - | Cliff's delta 0.006 |
| HEADLINE unsafe (any form) [RS-E1f]: removals per PR | Mann-Whitney U | 0.530 | 0.271 | 0.968 ns | - | Cliff's delta -0.000 |
| Tier A escape hatches: per 100 changed lines | Mann-Whitney U | 0.909 | 1.859 | 0.000235 *** | - | Cliff's delta 0.049 |
| Tier B escape hatches: per 100 changed lines | Mann-Whitney U | 2.888 | 3.818 | 0.113 ns | - | Cliff's delta 0.027 |
| suppression directives: share of PRs containing one | Chi-square | 0.138 | 0.062 | 3.94e-21 *** | - | Cramer's V 0.099 |
| escape hatches: usage profile (omnibus) | profile permutation (10,000x) | 3.601 | 5.321 | 0.0004 *** | - | Spearman rho 0.857 |
| unsafe (any form) [RS-E1f] | Mann-Whitney U | 0.212 | 0.480 | 0.78 ns | 0.78 | Cliff's delta 0.002 |
| transmute [RS-E2] | Mann-Whitney U | 0.020 | 0.058 | 0.209 ns | 0.238 | Cliff's delta -0.005 |
| _unchecked APIs [RS-E4] | Mann-Whitney U | 0.036 | 0.033 | 0.056 ns | 0.0747 | Cliff's delta 0.006 |
| .unwrap() / .expect() [RS-E5] | Mann-Whitney U | 2.533 | 2.779 | 9.87e-07 *** | 3.95e-06 | Cliff's delta 0.079 |
| panic! / todo! / unreachable! [RS-E6] | Mann-Whitney U | 0.111 | 0.413 | 0.00406 ** | 0.00812 | Cliff's delta 0.027 |
| as cast [RS-E8] | Mann-Whitney U | 0.641 | 1.288 | 3.16e-07 *** | 2.53e-06 | Cliff's delta 0.064 |
| RefCell / borrow_mut [RS-E9] | Mann-Whitney U | 0.035 | 0.237 | 0.00273 ** | 0.00727 | Cliff's delta -0.020 |
| dyn Any / downcast [RS-E10] | Mann-Whitney U | 0.013 | 0.034 | 0.00667 ** | 0.0107 | Cliff's delta 0.010 |

### RQ3 acceptance

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| acceptance: merged share | Chi-square | 0.612 | 0.822 | 4.7e-63 *** | - | Cramer's V 0.176 |
| acceptance within agent PRs: with vs without a Tier A escape hatch | Chi-square | 0.593 | 0.621 | 0.375 ns | - | Cramer's V 0.025 |
| acceptance within human PRs: with vs without a Tier A escape hatch | Chi-square | 0.818 | 0.823 | 0.652 ns | - | Cramer's V 0.005 |
| REPO-MATCHED acceptance: merged share (7 shared repos) | Fisher exact | 0.143 | 0.907 | 6.8e-11 *** | - | odds ratio 0.017 |
| acceptance: Claude_Code vs all humans | Chi-square | 0.681 | 0.822 | 0.00412 ** | - | Cramer's V 0.032 |
| acceptance: Copilot vs all humans | Chi-square | 0.499 | 0.822 | 8.88e-64 *** | - | Cramer's V 0.185 |
| acceptance: Cursor vs all humans | Chi-square | 0.500 | 0.822 | 1.31e-17 *** | - | Cramer's V 0.096 |
| acceptance: Devin vs all humans | Chi-square | 0.695 | 0.822 | 0.00128 ** | - | Cramer's V 0.036 |
| acceptance: OpenAI_Codex vs all humans | Chi-square | 0.719 | 0.822 | 2.89e-08 *** | - | Cramer's V 0.061 |

### Robustness

| Metric | Test | AI | Human | p | adj p | Effect |
|---|---|---|---|---|---|---|
| REPO-MATCHED unsafe (any form): per 100 changed lines (7 shared repos) | Mann-Whitney U | 0.145 | 0.215 | 0.142 ns | - | Cliff's delta 0.088 |
