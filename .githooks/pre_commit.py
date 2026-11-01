#!/usr/bin/env python3
"""
Noodle Gallery Tools - Tier 1 Fast Pre-Commit Quality Gate
Executes in < 1.5 seconds locally prior to any git commit.
Validates:
  1. Python syntax & compilation across all tools
  2. Secret & credential leak prevention
  3. Documentation relative link integrity (README.md, docs/)
  4. Shell script structure & sanity
"""

import os
import re
import sys
import py_compile
import subprocess
from pathlib import Path

# Safeguard Windows stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent

def run_cmd(cmd, cwd=REPO_ROOT):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def get_staged_files():
    code, stdout, _ = run_cmd(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"])
    if code != 0 or not stdout:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]

def check_python_syntax(staged_files):
    print("▶ [1/4] Checking Python Syntax & Compilation...")
    py_files = [f for f in staged_files if f.endswith(".py")]
    target_files = [REPO_ROOT / f for f in py_files] if py_files else list(REPO_ROOT.glob("**/*.py"))

    errors = []
    for f in target_files:
        if "venv" in f.parts or ".git" in f.parts or "__pycache__" in f.parts:
            continue
        if not f.exists():
            continue
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{f.relative_to(REPO_ROOT)}: {e}")

    if errors:
        print("❌ [FAIL] Python Syntax Errors detected:")
        for err in errors:
            print(f"   {err}")
        return False
    print("✅ [PASS] Python Syntax & Compilation")
    return True

def check_secret_leak(staged_files):
    print("▶ [2/4] Scanning for Leaked Credentials & Tokens...")
    secret_patterns = [
        (re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP)? PRIVATE KEY-----"), "Private Cryptographic Key"),
        (re.compile(r"(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})"), "GitHub Personal Access Token"),
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
        (re.compile(r"""(?:api_key|token|password|secret)\s*[:=]\s*["'](?!(?:\$\{[^}]+\}|example|changeme|default|test|your_api_key|your-api-key))[a-zA-Z0-9_\-\.\!@#\$%\^&\*]{20,}["']""", re.IGNORECASE), "Hardcoded Plaintext Secret"),
    ]

    target_files = [REPO_ROOT / f for f in staged_files] if staged_files else list(REPO_ROOT.glob("**/*"))
    errors = []

    for f in target_files:
        if f.is_dir() or "venv" in f.parts or ".git" in f.parts or ".jpg" in f.name or ".png" in f.name:
            continue
        if not f.exists():
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for pattern, name in secret_patterns:
                for line_no, line in enumerate(content.splitlines(), start=1):
                    if pattern.search(line):
                        errors.append(f"{f.relative_to(REPO_ROOT)}:{line_no} matches pattern '{name}'")
        except Exception as e:
            errors.append(f"Could not read {f.name}: {e}")

    if errors:
        print("❌ [FAIL] Potential secrets detected:")
        for err in errors:
            print(f"   {err}")
        return False
    print("✅ [PASS] Secret Sanitization Scan")
    return True

def check_docs_links():
    print("▶ [3/4] Validating Documentation Relative Links...")
    doc_files = [REPO_ROOT / "README.md"] + list(REPO_ROOT.glob("docs/**/*.md"))
    errors = []

    for doc in doc_files:
        if not doc.exists():
            continue
        content = doc.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r'\[([^\]]+)\]\(([^)#]+)(?:#[^\)]*)?\)', content)
        for text, target in links:
            if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
                continue
            target_path = (doc.parent / target).resolve()
            if not target_path.exists():
                errors.append(f"{doc.relative_to(REPO_ROOT)}: link '{text}' targets nonexistent '{target}'")

    if errors:
        print("❌ [FAIL] Broken documentation links:")
        for err in errors:
            print(f"   {err}")
        return False
    print("✅ [PASS] Documentation Links Integrity")
    return True

def check_shell_scripts():
    print("▶ [4/4] Verifying Shell Script Sanity...")
    sh_files = list(REPO_ROOT.glob("scripts/**/*.sh")) + list(REPO_ROOT.glob("scripts/**/*.sh.example"))
    errors = []
    for f in sh_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        if not content.startswith("#!/bin/bash") and not content.startswith("#!/usr/bin/env bash"):
            errors.append(f"{f.relative_to(REPO_ROOT)}: Missing bash shebang")
    if errors:
        print("❌ [FAIL] Shell script issues:")
        for err in errors:
            print(f"   {err}")
        return False
    print("✅ [PASS] Shell Script Sanity")
    return True

def main():
    print("==============================================================")
    print(" 🛡️  NOODLE GALLERY TOOLS - TIER 1 PRE-COMMIT VERIFICATION")
    print("==============================================================")
    staged = get_staged_files()
    success = (
        check_python_syntax(staged) and
        check_secret_leak(staged) and
        check_docs_links() and
        check_shell_scripts()
    )
    print("--------------------------------------------------------------")
    if not success:
        print("❌ PRE-COMMIT QUALITY GATE FAILED.")
        sys.exit(1)
    print("🎉 ALL PRE-COMMIT CHECKS PASSED: Proceeding with commit.")
    sys.exit(0)

if __name__ == "__main__":
    main()
