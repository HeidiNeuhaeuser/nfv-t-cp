# nfv-pp-sim

NFV performance profiling simulator. Used for research work on time-constraint NFV profiling (tc-profiling).

This repo is intended to be open sourced once the paper is submitted.

## Installation

* `python3 setup.py develop`

## Run

* `nfvppsim -c example_experiment.yaml`

## Combine Results

If the data frames of multiple parallel simulations should be combined do:

```bash
cd out/
python combine_results.py -i "experiment_*.pkl" -o myframe.pkl
```

* `NOTE`: The quotes for the file pattern are important!

## Plot

* `nfvppsim -c configs/cross_validation_panic.yaml --plot ../nfv-pp-sim-result-archive/results/2018-01-22_08-40_cross-validation-panic.pkl`

## Test

* `pytest`
* `pytest -v -s --log-level DEBUG`
* `pytest -v -s -k "midpoint"` (run tests that match keyword)

## Profiling

* `python -m cProfile -s cumtime run_profiling.py > profile.out`


## Contributor(s)

Manuel Peuster <manuel (at) peuster (dot) de

## License

Apache 2.0
