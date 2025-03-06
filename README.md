# xocto benchmarks data

This branch collects benchmarks data and contains scripts for working with that data.

This is an orphan branch, disjoint from main. It's recommended to use `git worktree` to
work on this branch separately from main.

```
git worktree add ../xocto-benchmarks-data benchmarks-data
```

Benchmarks data is added to this branch during CI and collected into the `benchmarks.csv` dataset.
For example, on pushes to main. See the workflows `run_benchmarks_main.yml` and `collect_benchmarks.yml` 
on main. 

This approach of collecting all benchmarks data into a single CSV living in version
control is not really scalable (though it's probably sufficient for xocto for a while). 
To scale this further we could make some progress by pruning the dataset (we don't need
to retain data forever). To really scale this though we'd probably need to move this data
out of version control and into e.g. S3 and an analytical database. 
