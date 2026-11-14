import importlib
import sys
import traceback

failed = 0
for mod_name in ("test_parser", "test_core"):
    mod = importlib.import_module(mod_name)
    for name in sorted(dir(mod)):
        if name.startswith("test_"):
            try:
                getattr(mod, name)()
                print("ok  ", mod_name, name)
            except Exception:
                failed += 1
                print("FAIL", mod_name, name)
                traceback.print_exc()
print("\nALL PASSED" if not failed else f"\n{failed} FAILED")
sys.exit(1 if failed else 0)
