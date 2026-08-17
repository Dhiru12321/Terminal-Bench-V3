#!/usr/bin/env python3
"""Advisory task similarity check using TF-IDF cosine similarity.

Compares a task against existing tasks in:
1. The local repo's tasks/ directory (excluding the task being checked)
2. One or more public reference repositories (configured below)

By default the scored document uses instruction prose only. An opt-in mode also
adds lightweight task-structure signals from task.toml metadata, visible file
names, and test names.

By default this is an advisory reviewer aid, not an acceptance gate. Use
--enforce-threshold to return a non-zero exit code when the advisory threshold
is exceeded.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rubric_review import build_similarity_document

SIMILARITY_ALERT_THRESHOLD = 0.80
# CUSTOMIZE — add reference repos to compare against for duplicate detection.
# Each entry is a Git URL. Tasks are expected under tasks/ by default.
# Append :. for repos with tasks at the repo root, or :subdir for other layouts.
# Examples:
#   "https://github.com/org/benchmark.git"           → tasks under tasks/
#   "https://github.com/org/task-collection.git:."    → tasks at repo root
REFERENCE_REPOS: list[str] = []


def load_task_documents(
    base_path: Path,
    exclude_task: str | None = None,
    *,
    include_structure_signals: bool = False,
) -> dict[str, str]:
    """Load similarity documents from task directories."""
    documents = {}
    if not base_path.exists():
        return documents

    for item in base_path.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name == "__pycache__":
            continue
        if exclude_task and item.name == exclude_task:
            continue
        if not (item / "instruction.md").exists():
            continue
        try:
            text = build_similarity_document(
                item,
                include_structure_signals=include_structure_signals,
            ).strip()
            if text:
                documents[item.name] = text
        except Exception as e:
            print(f"Warning: Failed to read {item}: {e}")
            continue

    return documents


def clone_repo(url: str, dest: Path) -> bool:
    """Shallow clone a reference repo."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Warning: Failed to clone {url}: {e}")
        return False


def parse_repo_entry(entry: str) -> tuple[str, str]:
    """Parse a REFERENCE_REPOS entry into (url, tasks_path).

    Supports:
      https://github.com/org/repo.git          → tasks under tasks/
      https://github.com/org/repo.git:subdir   → tasks under subdir/
      https://github.com/org/repo.git:.         → tasks at repo root
    """
    entry = entry.strip()
    # Split on the last colon that follows .git or the URL path
    # (avoid splitting on the colon in https://)
    if ".git:" in entry:
        url, path = entry.rsplit(".git:", 1)
        return url + ".git", path
    # Also handle URLs without .git suffix: look for a colon after the host/path
    parts = entry.split("://", 1)
    if len(parts) == 2 and ":" in parts[1].split("/")[-1]:
        # e.g. https://github.com/org/repo:subdir
        idx = entry.rfind(":")
        return entry[:idx], entry[idx + 1 :]
    return entry, "tasks"


def check_similarity(task_document: str, reference_documents: dict[str, str]) -> tuple[float, str]:
    """Compute TF-IDF cosine similarity against reference tasks.

    Returns (max_similarity, most_similar_task_name).
    """
    if not reference_documents:
        return 0.0, ""

    task_ids = list(reference_documents.keys())
    corpus = [reference_documents[tid] for tid in task_ids]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=5000,
        lowercase=True,
        strip_accents="unicode",
    )

    tb_vectors = vectorizer.fit_transform(corpus)
    new_vector = vectorizer.transform([task_document])
    similarities = cosine_similarity(new_vector, tb_vectors).flatten()

    max_idx = int(similarities.argmax())
    max_similarity = float(similarities[max_idx])
    most_similar_task = task_ids[max_idx]

    return max_similarity, most_similar_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Advisory similarity heuristic for tasks. By default it scores "
            "instruction prose only; use --include-structure to also score "
            "task.toml metadata, visible files, and test names."
        ),
    )
    parser.add_argument("target", type=Path, help="Task directory to compare")
    parser.add_argument(
        "--threshold",
        type=float,
        default=SIMILARITY_ALERT_THRESHOLD,
        help="Advisory similarity threshold as a 0-1 float (default: 0.80)",
    )
    parser.add_argument(
        "--enforce-threshold",
        action="store_true",
        help=(
            "Return exit code 1 when the advisory threshold is exceeded. "
            "Disabled by default because this check is not an acceptance gate "
            "yet."
        ),
    )
    parser.add_argument(
        "--include-structure",
        action="store_true",
        help=(
            "Also score task.toml metadata, visible file names, and test "
            "names alongside instruction prose."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_path = args.target
    instruction_path = task_path / "instruction.md"

    if not 0.0 <= args.threshold <= 1.0:
        print(f"Error: --threshold must be between 0 and 1, got {args.threshold}")
        return 1

    if not instruction_path.exists():
        print(f"Error: {instruction_path} not found")
        return 1

    instruction = instruction_path.read_text().strip()
    if not instruction:
        print(f"Error: {instruction_path} is empty")
        return 1

    task_document = build_similarity_document(
        task_path,
        include_structure_signals=args.include_structure,
    ).strip()
    if not task_document:
        print(f"Error: {instruction_path} is empty")
        return 1

    reference_documents: dict[str, str] = {}

    task_name = task_path.name
    local_tasks_dir = Path("tasks")
    if local_tasks_dir.exists():
        local = load_task_documents(
            local_tasks_dir,
            exclude_task=task_name,
            include_structure_signals=args.include_structure,
        )
        for tid, text in local.items():
            reference_documents[f"local/{tid}"] = text

    repos = [parse_repo_entry(r) for r in REFERENCE_REPOS]
    with tempfile.TemporaryDirectory() as tmp:
        for i, (repo_url, tasks_subdir) in enumerate(repos):
            repo_name = repo_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
            repo_path = Path(tmp) / f"ref-{i}-{repo_name}"
            if clone_repo(repo_url, repo_path):
                tasks_path = repo_path / tasks_subdir if tasks_subdir != "." else repo_path
                ref = load_task_documents(
                    tasks_path,
                    include_structure_signals=args.include_structure,
                )
                for tid, text in ref.items():
                    reference_documents[f"{repo_name}/{tid}"] = text
            else:
                print(f"Warning: Could not clone {repo_url}, skipping")

    if not reference_documents:
        print("No reference tasks found, skipping similarity check")
        return 0

    max_similarity, most_similar = check_similarity(task_document, reference_documents)
    similarity_pct = int(max_similarity * 100)
    threshold_pct = int(args.threshold * 100)

    mode = "instruction_plus_structure" if args.include_structure else "instruction_only"
    signal_summary = "instruction.md"
    if args.include_structure:
        signal_summary += " + task.toml metadata + visible file names + test names"

    print("Similarity mode: advisory reviewer signal")
    print(f"Review input: {mode}")
    print(f"Signals: {signal_summary}")
    print(
        f"Max similarity: {similarity_pct}% with '{most_similar}' "
        f"(advisory threshold: {threshold_pct}%)"
    )

    if max_similarity >= args.threshold:
        similarity_label = "structurally similar" if args.include_structure else "similar"
        print(
            f"Advisory: Candidate is {similarity_label} to '{most_similar}' "
            f"({similarity_pct}% >= {threshold_pct}%). Review manually for "
            "templating or shallow reuse."
        )
        if args.enforce_threshold:
            print("Error: --enforce-threshold enabled; exiting non-zero")
            return 1
        return 0

    print("No advisory similarity alert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
