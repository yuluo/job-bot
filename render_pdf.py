import argparse
import os
import subprocess
import sys
import tempfile
import time

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(html_path, pdf_path, timeout=60):
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.exists(html_path):
        raise FileNotFoundError(html_path)
    if not os.path.exists(CHROME):
        raise FileNotFoundError(f"Chrome not found at {CHROME}")

    os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen(
            [
                CHROME,
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={pdf_path}",
                f"file://{html_path}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Chrome writes the PDF but often does not exit on macOS; poll for a
        # file that has stopped growing, then terminate it ourselves.
        deadline = time.time() + timeout
        stable_size = -1
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if os.path.exists(pdf_path):
                size = os.path.getsize(pdf_path)
                if size > 0 and size == stable_size:
                    break
                stable_size = size
            time.sleep(0.5)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError(f"Chrome produced no PDF at {pdf_path}")
    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Render an HTML resume to PDF via headless Chrome")
    parser.add_argument("html", help="path to the resume HTML")
    parser.add_argument("--out", default=None, help="output PDF path (default: alongside the HTML)")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    out = args.out or os.path.splitext(args.html)[0] + ".pdf"
    try:
        path = render(args.html, out, args.timeout)
    except Exception as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"{path} ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    main()
