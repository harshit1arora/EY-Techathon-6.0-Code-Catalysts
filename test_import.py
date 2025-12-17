import traceback
try:
    import orchestrator
    print('Imported orchestrator OK')
except Exception:
    traceback.print_exc()
    raise