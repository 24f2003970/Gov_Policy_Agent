"""Run separately from API: one child parser at a time, persisted leases survive interruption."""
import argparse
import time
from app.config import Settings
from app.database import make_engine, schema_ready
from app.ingestion import reconcile, run_once

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    engine = make_engine(settings)
    try:
        if not schema_ready(engine):
            raise RuntimeError("Run explicit migrations before starting worker")
        if args.reconcile:
            print(f"Reconciled {reconcile(engine, settings)} expired orphan files")
        elif args.once:
            print("Processed one available job" if run_once(engine, settings) else "No eligible job")
        else:
            print("Worker running; one job at a time. Ctrl+C to stop.", flush=True)
            while True:
                try:
                    if not run_once(engine, settings):
                        time.sleep(2)
                except Exception:
                    print("Worker unavailable; will reconnect. No private error details logged.", flush=True)
                    time.sleep(5)
    except KeyboardInterrupt:
        print("Worker stopped. Expired leases recover on restart.")
    finally:
        engine.dispose()
