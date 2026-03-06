"""
NPDC Dataset Quality Audit

Checks:
1. Test datasets
2. Duplicate datasets
3. Datasets without scientists
4. Incomplete datasets
5. Empty datasets

Shows:
- Submitter name
- Submission date and time

Generates CSV report automatically.

Usage:
    python manage.py shell < dataset_quality_audit.py
"""

import os
import django
import csv
from datetime import datetime
from collections import defaultdict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "npdc_site.settings")
django.setup()

from data_submission.models import DatasetSubmission


REPORT_FILE = "npdc_dataset_audit_report.csv"


def safe(value, default="NULL"):
    if value is None or value == "":
        return default
    return str(value)


def get_submitter(ds):
    submitter = getattr(ds, "submitter", None)

    if submitter:
        try:
            return submitter.get_full_name() or submitter.username
        except:
            return str(submitter)

    return "Unknown"


def get_submission_time(ds):
    date = getattr(ds, "submission_date", None)
    if date:
        return str(date)
    return "NULL"


def audit_dataset_quality():

    print("=" * 110)
    print("NPDC DATASET QUALITY AUDIT")
    print("=" * 110)
    print(f"Scan started: {datetime.now()}\n")

    datasets = DatasetSubmission.objects.all()

    test_datasets = []
    empty_datasets = []
    incomplete_datasets = []
    no_scientists = []

    title_map = defaultdict(list)

    report_rows = []

    # -------------------------
    # SCAN DATASETS
    # -------------------------

    for ds in datasets:

        title = (ds.title or "").strip()
        abstract = (ds.abstract or "").strip()

        title_lower = title.lower()

        metadata_id = safe(ds.metadata_id)
        submitter = get_submitter(ds)
        submitted = get_submission_time(ds)

        # TEST DATASETS
        if (
            title_lower.startswith("test")
            or "test metadata" in title_lower
            or "sample dataset - test metadata" in title_lower
            or "testing" in title_lower
        ):
            test_datasets.append(ds)

            report_rows.append([
                "TEST DATASET",
                ds.id,
                metadata_id,
                submitter,
                submitted,
                title
            ])

        # EMPTY DATASETS
        if not title and not abstract:

            empty_datasets.append(ds)

            report_rows.append([
                "EMPTY DATASET",
                ds.id,
                metadata_id,
                submitter,
                submitted,
                "EMPTY"
            ])

        # INCOMPLETE DATASETS
        category = getattr(ds, "category", None)
        iso_topic = getattr(ds, "iso_topic", None)

        if not title or not abstract or not category or not iso_topic:

            incomplete_datasets.append(ds)

            report_rows.append([
                "INCOMPLETE DATASET",
                ds.id,
                metadata_id,
                submitter,
                submitted,
                title
            ])

        # DATASETS WITHOUT SCIENTISTS
        try:
            if ds.scientists.count() == 0:

                no_scientists.append(ds)

                report_rows.append([
                    "NO SCIENTIST",
                    ds.id,
                    metadata_id,
                    submitter,
                    submitted,
                    title
                ])
        except:
            pass

        # DUPLICATE CHECK
        if title:
            title_map[title.lower()].append(ds)

    duplicate_groups = [group for group in title_map.values() if len(group) > 1]

    for group in duplicate_groups:

        for ds in group:

            report_rows.append([
                "DUPLICATE DATASET",
                ds.id,
                safe(ds.metadata_id),
                get_submitter(ds),
                get_submission_time(ds),
                safe(ds.title)
            ])

    # -------------------------
    # PRINT SUMMARY
    # -------------------------

    print("SUMMARY")
    print("-" * 60)

    print("Test datasets:", len(test_datasets))
    print("Duplicate dataset groups:", len(duplicate_groups))
    print("Datasets without scientists:", len(no_scientists))
    print("Incomplete datasets:", len(incomplete_datasets))
    print("Empty datasets:", len(empty_datasets))

    # -------------------------
    # GENERATE REPORT
    # -------------------------

    print("\nGenerating CSV report...")

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Issue Type",
            "Dataset ID",
            "Metadata ID",
            "Submitter",
            "Submission Date & Time",
            "Title"
        ])

        writer.writerows(report_rows)

    print("Report generated successfully:")
    print(REPORT_FILE)
    print("=" * 110)


if __name__ == "__main__":
    audit_dataset_quality()