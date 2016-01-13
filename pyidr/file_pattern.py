"""
Bio-Formats style file patterns.

www.openmicroscopy.org/site/support/bio-formats5.1/formats/pattern-file.html
"""

import re
import string
from itertools import product, izip_longest


class InvertedRangeError(Exception):
    pass


def _expand_letter_range(start, stop, step):
    if not(start.isalpha() and stop.isalpha()):
        raise ValueError("non-literal range: %s-%s" % (start, stop))
    if (start.isupper() != stop.isupper()):
        raise ValueError("mixed case range: %s-%s" % (start, stop))
    letters = string.uppercase if start.isupper() else string.lowercase
    start = letters.index(start)
    stop = letters.index(stop) + 1
    if stop <= start:
        raise InvertedRangeError
    return [letters[_] for _ in xrange(start, stop, step)]


def expand_range(r):
    try:
        r, step = r.strip().split(":")
    except ValueError:
        step = 1
    else:
        try:
            step = int(step)
        except ValueError:
            raise ValueError("non-numeric step: %r" % (step,))
    r = r.strip()
    try:
        start, stop = r.split("-")
    except ValueError:
        return [r]
    try:
        start_str = start
        start = int(start)
    except ValueError:
        try:
            return _expand_letter_range(start, stop, step)
        except InvertedRangeError:
            raise ValueError("inverted range: %s" % r)
    else:
        stop_str = stop
        stop = int(stop) + 1
        if stop <= start:
            raise ValueError("inverted range: %s" % r)
        step = int(step)
        if len(start_str) != len(stop_str):
            return map(str, range(start, stop, step))
        else:
            fmt = "%%0%dd" % len(start_str)
            return [fmt % _ for _ in xrange(start, stop, step)]


def expand_block(block):
    return sum((expand_range(_.strip()) for _ in block.split(",")), [])


# FIXME: this can be optimized, e.g., pre-calc whole step list
def build_numeric_block(values):
    if not values:
        return ""
    N = len(values)
    values = sorted(values, key=int)
    if N < 2:
        return values[0]
    if N < 3:
        return "<%s>" % ",".join(values)
    i = N - 2
    intervals = []
    while i >= 0:
        rstep = int(values[i+1]) - int(values[i])
        if i == 0:
            lstep = rstep + 1  # set to something != rstep
        else:
            lstep = int(values[i]) - int(values[i-1])
        if lstep != rstep:
            intervals.append("%s-%s%s" % (
                values[i], values[-1], ":%d" % rstep if rstep > 1 else ""
            ))
            del values[i:]
            i -= 1
        i -= 1
    return "<%s>" % ",".join(reversed(intervals))


def find_numeric_pattern(names, base=None):
    if not names:
        return ""
    if base is None:
        base = names[0]
    if len(names) < 2:
        return base
    matches = list(re.finditer(r"\d+", base))
    if not matches:
        return base
    pattern = [base[:matches[0].start()]]
    for i, m in enumerate(matches):
        regex = re.compile(r"^%s(\d+)%s$" % (base[:m.start()], base[m.end():]))
        values = set()
        for n in names:
            try:
                values.add(regex.match(n).groups()[0])
            except (AttributeError, IndexError):
                pass
        pattern.append(build_numeric_block(values))
        try:
            next_start = matches[i+1].start()
        except IndexError:
            next_start = len(base)
        pattern.append(base[m.end():next_start])
    return "".join(pattern)


class FilePattern(object):

    def __init__(self, pattern):
        self.pattern = pattern

    def blocks(self):
        return re.findall(r"<(.+?)>", self.pattern)

    def filenames(self):
        fixed = re.split(r"<.+?>", self.pattern)
        for repl in product(*(expand_block(_) for _ in self.blocks())):
            yield "".join(sum(izip_longest(fixed, repl, fillvalue=""), ()))
