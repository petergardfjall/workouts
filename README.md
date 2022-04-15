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

``` bash
./workouts --help
```

# Development

Use `LOG_LEVEL=debug` to get debug output.
