import pstats
import sys

p = pstats.Stats("profile_bf.prof")
p.sort_stats("cumtime")
p.print_stats(40)
print("\nDone")
