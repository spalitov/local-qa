import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from qa.input_loader import load_audit_input

def main():
    try:
        if len(sys.argv) < 2:
            print(
                "Usage: python scripts/run_audit.py <input.json|input.csv> [--row N] [--send-id ID]",
                file=sys.stderr,
            )
            sys.exit(1)

        p = Path(sys.argv[1])
        row_num = 1
        send_id = None

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--row":
                if i + 1 >= len(sys.argv):
                    raise ValueError("--row requires a numeric value.")
                row_num = int(sys.argv[i + 1])
                i += 2
                continue
            if arg == "--send-id":
                if i + 1 >= len(sys.argv):
                    raise ValueError("--send-id requires a value.")
                send_id = sys.argv[i + 1]
                i += 2
                continue
            raise ValueError(f"Unknown argument: {arg}")

        from qa.pipeline import run_audit
        audit_in = load_audit_input(p, row_num=row_num, send_id=send_id)

        out = run_audit(audit_in)
        print(out.model_dump_json(indent=2))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
