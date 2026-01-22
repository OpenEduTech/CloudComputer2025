import os
import py_compile


def main() -> int:
    root = "/app"
    bad: list[tuple[str, str]] = []

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            try:
                py_compile.compile(path, doraise=True)
            except Exception as exc:  # pragma: no cover
                bad.append((path, f"{type(exc).__name__}: {exc}"))

    print(f"BAD={len(bad)}")
    for path, err in bad[:200]:
        print(f"{path} -> {err}")

    return 0 if not bad else 2


if __name__ == "__main__":
    raise SystemExit(main())
