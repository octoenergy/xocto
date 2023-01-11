# Ranges

## A utility for working with ranges

The basic building block of the module is the `Range` class.

## Usage

A few examples:

```python
from xocto.ranges import Range, RangeBoundaries

>>> Range(0, 2, boundaries=RangeBoundaries.EXCLUSIVE_INCLUSIVE)
<Range: (0,2]>
>>> Range(0, 2, boundaries="[]")
<Range: [0,2]>
>>> sorted([Range(1, 4), Range(0, 5)])
[<Range: [0,5)>, <Range: [1,4)>]
>>> sorted([Range(1, 2), Range(None, 2)])
[<Range: [None,2)>, <Range: [1,2)>]
>>> sorted([Range(3, 5), Range(3, 4)])
[<Range: [3,4)>, <Range: [4,5)>]
```

See [xocto.ranges](https://github.com/octoenergy/xocto/blob/master/xocto/ranges.py) for more details, including examples and in depth technical details.
