import importlib.util

print("numba present:", importlib.util.find_spec("numba") is not None)
