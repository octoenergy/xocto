# Ranges

## A utility for working with ranges

The basic building block of the module is the `Range` class.

## Usage

A few examples:

```python
from xocto.ranges import Range, RangeBoundaries
> > > Range(0, 2, boundaries=RangeBoundaries.EXCLUSIVE_INCLUSIVE)
> > > <Range: (0,2]>
> > > 0 in Range(0, 2)
> > > True
> > > 2 in Range(0, 2)
> > > False
> > > date(2020, 1, 1) in Range(date(2020, 1, 2), date(2020, 1, 5))
> > > False
> > > sorted([Range(1, 4), Range(0, 5)])
> > > [<Range: [0,5)>, <Range: [1,4)>]
```

See [xocto.ranges](https://github.com/octoenergy/xocto/blob/master/xocto/ranges.py) for more details, including examples and in depth technical details.

## API Reference

```{eval-rst}
.. automodule:: xocto.ranges
   :members:
   :undoc-members:
   :show-inheritance:
```
