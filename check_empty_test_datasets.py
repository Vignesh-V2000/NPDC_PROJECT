"""
Delete Test Datasets Safely

Steps:
1. List all test datasets
2. Ask confirmation
3. Delete only if user types 'yes'

Usage:
    python manage.py shell < delete_test_datasets.py
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "npdc_site.settings")
django.setup()

from data_submission.models import DatasetSubmission


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


def delete_test_datasets():

    test_datasets = DatasetSubmission.objects.filter(
        title__icontains="test"
    )

    count = test_datasets.count()

    print("\nTEST DATASETS FOUND:", count)
    print("=" * 100)

    if count == 0:
        print("No test datasets found.")
        return

    for ds in test_datasets:

        print(
            f"ID:{ds.id:5d} | "
            f"MID:{safe(ds.metadata_id):25s} | "
            f"Submitter:{safe(get_submitter(ds)):25s} | "
            f"Submitted:{safe(get_submission_time(ds)):20s} | "
            f"Title:{safe(ds.title)}"
        )

    print("=" * 100)

    confirm = input("\nType YES to delete these datasets: ")

    if confirm == "YES":

        deleted = test_datasets.count()

        test_datasets.delete()

        print("\nDeleted test datasets:", deleted)

    else:

        print("\nDeletion cancelled.")


if __name__ == "__main__":
    delete_test_datasets()