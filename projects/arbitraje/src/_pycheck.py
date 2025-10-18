import py_compile,traceback
try:
    py_compile.compile('arbitraje/arbitrage_report_ccxt.py', doraise=True)
    print('COMPILE_OK')
except Exception:
    traceback.print_exc()
