import argparse
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def run_pytest(repo_root: Path, reports_dir: Path) -> int:
    reports_dir.mkdir(parents=True, exist_ok=True)
    junit_path = reports_dir / "junit.xml"
    coverage_xml = reports_dir / "coverage.xml"
    coverage_html_dir = reports_dir / "coverage-html"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests",
        "--maxfail=1",
        f"--junitxml={junit_path}",
        "--asyncio-mode=auto",
        "--cov=app",
        "--cov=main",
        f"--cov-report=xml:{coverage_xml}",
        f"--cov-report=html:{coverage_html_dir}",
        "--cov-report=term-missing",
    ]
    return subprocess.run(cmd, cwd=repo_root).returncode


def parse_junit(junit_file: Path) -> dict:
    if not junit_file.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    tree = ET.parse(junit_file)
    root = tree.getroot()
    if root.tag == "testsuites":
        tests = sum(int(ts.attrib.get("tests", 0)) for ts in root)
        failures = sum(int(ts.attrib.get("failures", 0)) for ts in root)
        errors = sum(int(ts.attrib.get("errors", 0)) for ts in root)
        skipped = sum(int(ts.attrib.get("skipped", 0)) for ts in root)
        time = sum(float(ts.attrib.get("time", 0.0)) for ts in root)
    else:
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        skipped = int(root.attrib.get("skipped", 0))
        time = float(root.attrib.get("time", 0.0))
    return {"tests": tests, "failures": failures, "errors": errors, "skipped": skipped, "time": time}


def parse_coverage(coverage_xml: Path) -> float:
    if not coverage_xml.exists():
        return 0.0
    root = ET.parse(coverage_xml).getroot()
    line_rate = root.attrib.get("line-rate")
    try:
        return round(float(line_rate) * 100.0, 2) if line_rate is not None else 0.0
    except Exception:
        return 0.0


def write_markdown(report_md: Path, junit_stats: dict, coverage_pct: float) -> None:
    lines = [
        "# gateway-api Test Report\n",
        f"- Total tests: {junit_stats['tests']}\n",
        f"- Failures: {junit_stats['failures']}\n",
        f"- Errors: {junit_stats['errors']}\n",
        f"- Skipped: {junit_stats['skipped']}\n",
        f"- Duration (s): {round(junit_stats['time'], 3)}\n",
        f"- Line coverage: {coverage_pct}%\n",
    ]
    report_md.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    repo_root = Path(__file__).parent
    reports_dir = repo_root / args.reports_dir
    code = run_pytest(repo_root, reports_dir)
    junit_stats = parse_junit(reports_dir / "junit.xml")
    coverage_pct = parse_coverage(reports_dir / "coverage.xml")
    write_markdown(reports_dir / "test-report.md", junit_stats, coverage_pct)
    print(f"JUnit XML: {reports_dir / 'junit.xml'}")
    print(f"Coverage XML: {reports_dir / 'coverage.xml'}")
    print(f"Coverage HTML: {reports_dir / 'coverage-html'}/index.html")
    print(f"Markdown Report: {reports_dir / 'test-report.md'}")
    sys.exit(code)


if __name__ == "__main__":
    main()
