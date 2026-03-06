import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from qa.input_loader import load_audit_input


def _print_usage() -> None:
    print(
        (
            "Usage: python scripts/run_audit.py <input.json|input.csv> "
            "[--row N] [--send-id ID] [--all] [--out-dir DIR]\n"
            "Defaults: audits all rows/scenarios and writes timestamped files to ./output"
        ),
        file=sys.stderr,
    )


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def _count_json_rows(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("scenarios"), list):
        return len(data["scenarios"])
    return 1


def _count_input_rows(path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _count_csv_rows(path)
    if suffix == ".json":
        return _count_json_rows(path)
    raise ValueError(f"Unsupported input file type: {path.suffix}. Use .json or .csv.")


def _flatten_for_csv(obj: dict) -> dict:
    local = obj.get("local", {})
    llm = obj.get("llm", {})
    return {
        "id": obj.get("id", ""),
        "preferred_tone": obj.get("preferred_tone", ""),
        "blocklisted_words": json.dumps(obj.get("blocklisted_words", []), ensure_ascii=False),
        "audited_agent_message": obj.get("audited_agent_message", ""),
        "correct_grammar": local.get("correct_grammar", ""),
        "no_typos": local.get("no_typos", ""),
        "no_repetition": local.get("no_repetition", ""),
        "grammar_error_count": local.get("grammar_error_count", ""),
        "typo_count": local.get("typo_count", ""),
        "repetition_max_cosine": local.get("repetition_max_cosine", ""),
        "understandable": llm.get("understandable", ""),
        "preferred_tone_followed": llm.get("preferred_tone_followed", ""),
        "empathy": llm.get("empathy", ""),
        "personalization": llm.get("personalization", ""),
        "finding": llm.get("finding", ""),
        "conversation_json": json.dumps(obj.get("conversation", []), ensure_ascii=False),
        "llm_raw_json": json.dumps(obj.get("llm_raw", {}), ensure_ascii=False),
    }


def _write_outputs(results: list[dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"audited-{stamp}.json"
    csv_path = out_dir / f"audited-{stamp}.csv"

    json_path.write_text(f"{json.dumps(results, indent=2, ensure_ascii=False)}\n", encoding="utf-8")

    rows = [_flatten_for_csv(r) for r in results]
    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(results)} audit result(s) to {json_path}")
    print(f"Wrote {len(results)} audit result(s) to {csv_path}")


def main():
    try:
        if len(sys.argv) < 2:
            _print_usage()
            sys.exit(1)

        p = Path(sys.argv[1])
        row_num = 1
        row_set = False
        send_id = None
        audit_all = True
        explicit_all = False
        out_dir: Path | None = Path("output")

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg in ("-h", "--help"):
                _print_usage()
                sys.exit(0)
            if arg == "--all":
                explicit_all = True
                audit_all = True
                i += 1
                continue
            if arg == "--out-dir":
                if i + 1 >= len(sys.argv):
                    raise ValueError("--out-dir requires a directory path.")
                out_dir = Path(sys.argv[i + 1])
                i += 2
                continue
            if arg == "--row":
                if i + 1 >= len(sys.argv):
                    raise ValueError("--row requires a numeric value.")
                row_num = int(sys.argv[i + 1])
                row_set = True
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

        if audit_all and send_id:
            raise ValueError("Use either --all or --send-id, not both.")

        if not explicit_all and (row_set or send_id is not None):
            audit_all = False

        if audit_all:
            total = _count_input_rows(p)
            if total < 1:
                raise ValueError("No rows found in input.")

            results: list[dict] = []
            failures: list[str] = []

            for idx in tqdm(range(1, total + 1), desc="Auditing", unit="row"):
                try:
                    audit_in = load_audit_input(p, row_num=idx)
                    out = run_audit(audit_in)
                    results.append(out.model_dump())
                except Exception as row_exc:
                    failures.append(f"row {idx}: {row_exc}")

            if not results:
                raise ValueError(
                    "All rows failed during audit. First failure: "
                    f"{failures[0] if failures else 'unknown error'}"
                )

            _write_outputs(results, out_dir or Path("output"))

            if failures:
                print(
                    f"Warning: {len(failures)} row(s) failed. First failure: {failures[0]}",
                    file=sys.stderr,
                )
            return

        audit_in = load_audit_input(p, row_num=row_num, send_id=send_id)
        out = run_audit(audit_in).model_dump()

        _write_outputs([out], out_dir or Path("output"))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
