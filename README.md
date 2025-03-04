# xocto benchmarks data

This branch collects benchmarks data and contains scripts for working with that data.

This is an orphan branch, disjoint from main. It's recommended to use git worktree to
work on this branch separately from main.

```
git worktree add ../xocto-benchmarks-data benchmarks-data
```

Benchmarks data is added to this branch during CI, for example on pushes to main. See the
workflows `run_benchmarks_main.yml` and `collect_benchmarks.yml` on main.
