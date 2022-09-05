# About

`workouts` extracts interval sequences from activities backed-up by
[garminexport](https://github.com/petergardfjall/garminexport).

Output is given as [CSV](https://en.wikipedia.org/wiki/Comma-separated_values)
and summarizes both interval laps and recovery laps. Individual laps can be
output with `LOG_LEVEL=debug`.

What constitues an interval-paced lap can be defined through `--interval-pace`
(defaults to `04:15` min/km) and `--min-interval-distance` (defaults to `150`
meters to avoid counting strides as intervals).

For full details on its usage run:

```bash
./workouts --help
```

# Development

Use `LOG_LEVEL=debug` to get debug output.

# Convenience scripts

A couple of convenience scripts are also included:

- `pace.py`: given a time and distance, calculates the pace.

  ```bash
  ./pace.py 35:00 10000
  ```

- `pacer.py`: a simple script for calculating target paces to run at as a given
  percentage of a certain source pace (such as your 5K pace).

  Sample use: my current 5K race result is 03:50 min/km and I want to find out
  what pace to train at if I want to train at 104%, 95% and 90% of the 5K pace,
  respectively.

  ```bash
  ./pacer.py 03:50 104 95 90
  ```
