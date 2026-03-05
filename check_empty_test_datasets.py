"""
Script to identify empty or test datasets in the NPDC database.

This script helps identify datasets that might be:
- Test/demo datasets
- Incomplete submissions
- Placeholder records
- Datasets with minimal content
- Datasets with suspicious patterns indicating they're for testing

Usage (don't run yet):
    python manage.py shell < check_empty_test_datasets.py
    
    Or in Django shell:
    exec(open('check_empty_test_datasets.py').read())
"""

import os
import django
from django.db import connection
from collections import defaultdict
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from data_submission.models import DatasetSubmission


class DatasetAudit:
    """Audit datasets for empty/test content"""
    
    def __init__(self):
        self.test_keywords = [
            'test', 'demo', 'sample', 'dummy', 'placeholder',
            'example', 'temp', 'temporary', 'trial', 'beta',
            'sandbox', 'development', 'dev', 'staging',
            'qc_', 'qa_', 'test_', 'tmp_', 'delete_', 'remove_'
        ]
        
        self.findings = {
            'empty_title': [],
            'empty_abstract': [],
            'minimal_metadata': [],
            'test_keywords': [],
            'no_files': [],
            'no_scientists': [],
            'no_temporal_coverage': [],
            'no_spatial_coverage': [],
            'very_new': [],
            'placeholder_patterns': [],
        }
    
    def run_full_audit(self):
        """Run complete audit - only incomplete, test, or empty metadata datasets"""
        print("=" * 80)
        print("NPDC DATASET AUDIT - Incomplete/Test/Empty Metadata Detection")
        print("=" * 80)
        print(f"Scan started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get all datasets
        all_datasets = DatasetSubmission.objects.all()
        total = all_datasets.count()
        print(f"Total datasets to scan: {total}\n")
        
        # Run checks - only for incomplete, test, or empty metadata
        print("Running checks for: Incomplete, Test, or Empty Metadata datasets...\n")
        self._check_empty_title(all_datasets)
        self._check_empty_abstract(all_datasets)
        self._check_minimal_metadata(all_datasets)
        self._check_test_keywords(all_datasets)
        self._check_placeholder_patterns(all_datasets)
        self._check_very_new(all_datasets)
        
        # Print results
        self._print_results()
    
    def _check_empty_title(self, qs):
        """Check datasets with empty or minimal titles"""
        datasets = qs.filter(title__isnull=True) | qs.filter(title='') | qs.filter(title__regex=r'^\s*$')
        self.findings['empty_title'] = list(datasets.values_list('id', 'metadata_id', 'title', 'status'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with EMPTY TITLE")
    
    def _check_empty_abstract(self, qs):
        """Check datasets with empty abstracts"""
        datasets = qs.filter(abstract__isnull=True) | qs.filter(abstract='')
        self.findings['empty_abstract'] = list(datasets.values_list('id', 'metadata_id', 'title', 'status'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with EMPTY ABSTRACT")
    
    def _check_minimal_metadata(self, qs):
        """Check datasets with minimal metadata (missing category, iso_topic, etc.)"""
        datasets = qs.filter(
            category__isnull=True
        ) | qs.filter(
            iso_topic__isnull=True
        ) | qs.filter(
            category=''
        ) | qs.filter(
            iso_topic=''
        )
        self.findings['minimal_metadata'] = list(datasets.values_list('id', 'metadata_id', 'title', 'category', 'iso_topic'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with MINIMAL METADATA")
    
    def _check_test_keywords(self, qs):
        """Check for test/demo keywords in title or abstract"""
        test_datasets = []
        for dataset in qs:
            dataset_text = f"{dataset.title or ''} {dataset.abstract or ''}".lower()
            for keyword in self.test_keywords:
                if keyword in dataset_text:
                    test_datasets.append((dataset.id, dataset.metadata_id, dataset.title, keyword))
                    break
        
        self.findings['test_keywords'] = test_datasets
        if test_datasets:
            print(f"  ⚠ Found {len(test_datasets)} datasets with TEST/DEMO KEYWORDS")
    
    def _check_no_files(self, qs):
        """Check datasets with no files"""
        datasets = qs.filter(number_of_files__isnull=True) | qs.filter(number_of_files=0)
        self.findings['no_files'] = list(datasets.values_list('id', 'metadata_id', 'title', 'number_of_files'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with NO FILES")
    
    def _check_no_scientists(self, qs):
        """Check datasets with no associated scientists"""
        datasets = []
        for dataset in qs:
            if dataset.scientists.count() == 0:
                datasets.append((dataset.id, dataset.metadata_id, dataset.title))
        
        self.findings['no_scientists'] = datasets
        if datasets:
            print(f"  ⚠ Found {len(datasets)} datasets with NO SCIENTISTS")
    
    def _check_no_temporal_coverage(self, qs):
        """Check datasets missing temporal coverage"""
        datasets = qs.filter(
            temporal_start_date__isnull=True
        ) | qs.filter(
            temporal_end_date__isnull=True
        )
        self.findings['no_temporal_coverage'] = list(datasets.values_list('id', 'metadata_id', 'title', 'temporal_start_date', 'temporal_end_date'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with NO TEMPORAL COVERAGE")
    
    def _check_no_spatial_coverage(self, qs):
        """Check datasets missing spatial coverage"""
        datasets = qs.filter(
            west_longitude__isnull=True
        ) | qs.filter(
            east_longitude__isnull=True
        ) | qs.filter(
            south_latitude__isnull=True
        ) | qs.filter(
            north_latitude__isnull=True
        )
        self.findings['no_spatial_coverage'] = list(datasets.values_list('id', 'metadata_id', 'title'))
        if datasets.exists():
            print(f"  ⚠ Found {datasets.count()} datasets with NO SPATIAL COVERAGE")
    
    def _check_very_new(self, qs):
        """Check very recently created datasets (might be incomplete)"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        datasets = qs.filter(submission_date__gte=thirty_days_ago)
        
        # Further filter: new AND draft (more likely to be incomplete)
        incomplete_new = datasets.filter(status__in=['draft', 'submitted'])
        
        self.findings['very_new'] = list(incomplete_new.values_list('id', 'metadata_id', 'title', 'status', 'submission_date'))
        if incomplete_new.exists():
            print(f"  ⚠ Found {incomplete_new.count()} INCOMPLETE datasets created in last 30 days")
    
    def _check_placeholder_patterns(self, qs):
        """Check for placeholder/suspicious patterns"""
        placeholder_patterns = [
            'N/A', 'n/a', 'TBD', 'tbd', 'TODO', 'todo',
            'xxx', 'XXX', '...', '***', '???', 'pending',
            'FIXME', 'fixme', 'unknown', 'Unknown', 'UNKNOWN'
        ]
        
        suspicious_datasets = []
        for dataset in qs:
            text = f"{dataset.title or ''} {dataset.abstract or ''}".lower()
            for pattern in placeholder_patterns:
                if pattern.lower() in text:
                    suspicious_datasets.append((dataset.id, dataset.metadata_id, dataset.title, pattern))
                    break
        
        self.findings['placeholder_patterns'] = suspicious_datasets
        if suspicious_datasets:
            print(f"  ⚠ Found {len(suspicious_datasets)} datasets with PLACEHOLDER PATTERNS")
    
    def _print_results(self):
        """Print detailed results - only incomplete, test, or empty metadata"""
        print("\n" + "=" * 80)
        print("DATASETS WITH INCOMPLETE/TEST/EMPTY METADATA")
        print("=" * 80)
        
        # Empty titles
        if self.findings['empty_title']:
            print("\n1. EMPTY TITLE (" + str(len(self.findings['empty_title'])) + ")")
            print("-" * 80)
            for id, mid, title, status in self.findings['empty_title']:
                print(f"  ID: {id:5d} | MID: {mid:30s} | Status: {status:15s}")
        
        # Empty abstract
        if self.findings['empty_abstract']:
            print("\n2. EMPTY ABSTRACT (" + str(len(self.findings['empty_abstract'])) + ")")
            print("-" * 80)
            for id, mid, title, status in self.findings['empty_abstract']:
                print(f"  ID: {id:5d} | Title: {title[:50] if title else 'None':50s} | Status: {status:15s}")
        
        # Minimal metadata
        if self.findings['minimal_metadata']:
            print("\n3. MINIMAL METADATA (" + str(len(self.findings['minimal_metadata'])) + ")")
            print("-" * 80)
            for id, mid, title, cat, iso in self.findings['minimal_metadata']:
                print(f"  ID: {id:5d} | MID: {mid:30s} | Category: {str(cat)[:15]:15s} | ISO: {str(iso)[:15]:15s}")
        
        # Test keywords
        if self.findings['test_keywords']:
            print("\n4. TEST/DEMO KEYWORDS (" + str(len(self.findings['test_keywords'])) + ")")
            print("-" * 80)
            for id, mid, title, keyword in self.findings['test_keywords']:
                print(f"  ID: {id:5d} | Keyword: {keyword:20s} | Title: {title[:45] if title else 'None':45s}")
        
        # Placeholder patterns
        if self.findings['placeholder_patterns']:
            print("\n5. PLACEHOLDER PATTERNS (" + str(len(self.findings['placeholder_patterns'])) + ")")
            print("-" * 80)
            for id, mid, title, pattern in self.findings['placeholder_patterns']:
                print(f"  ID: {id:5d} | Pattern: {pattern:20s} | Title: {title[:40] if title else 'None':40s}")
        
        # Very new datasets (incomplete)
        if self.findings['very_new']:
            print("\n6. INCOMPLETE DATASETS (created in last 30 days) (" + str(len(self.findings['very_new'])) + ")")
            print("-" * 80)
            for id, mid, title, status, submit_date in self.findings['very_new']:
                print(f"  ID: {id:5d} | Status: {status:15s} | Created: {str(submit_date)[:10]:10s} | Title: {title[:40] if title else 'None':40s}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        empty_title_count = len(self.findings['empty_title'])
        empty_abstract_count = len(self.findings['empty_abstract'])
        minimal_meta_count = len(self.findings['minimal_metadata'])
        test_keywords_count = len(self.findings['test_keywords'])
        placeholder_count = len(self.findings['placeholder_patterns'])
        incomplete_count = len(self.findings['very_new'])
        
        print(f"  • Empty Title:             {empty_title_count}")
        print(f"  • Empty Abstract:          {empty_abstract_count}")
        print(f"  • Minimal Metadata:        {minimal_meta_count}")
        print(f"  • Test/Demo Keywords:      {test_keywords_count}")
        print(f"  • Placeholder Patterns:    {placeholder_count}")
        print(f"  • Incomplete (Recent):     {incomplete_count}")
        print(f"  " + "-" * 76)
        
        total_issues = empty_title_count + empty_abstract_count + minimal_meta_count + test_keywords_count + placeholder_count + incomplete_count
        print(f"  TOTAL PROBLEMATIC DATASETS: {total_issues}")
        
        print("\nRecommended Actions:")
        print("  1. Review and delete test/demo datasets (test_keywords)")
        print("  2. Complete or delete datasets with empty title/abstract")
        print("  3. Fill in missing category/ISO topic or delete incomplete records")
        print("  4. Remove placeholder content (TBD, N/A, TODO, etc.)")
        print("  5. Follow up on incomplete submissions (recent drafts)")
        
        print("\n" + "=" * 80)
        print("END OF AUDIT")
        print("=" * 80)
    
    def export_to_csv(self, filename='dataset_audit_results.csv'):
        """Export findings to CSV for review"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Issue Type', 'Dataset ID', 'Metadata ID', 'Title', 'Status', 'Details'])
            
            for issue_type, datasets in self.findings.items():
                for dataset in datasets:
                    if isinstance(dataset, tuple):
                        writer.writerow([issue_type] + list(dataset))
        
        print(f"\nResults exported to: {filename}")


if __name__ == '__main__':
    # Create auditor and run
    auditor = DatasetAudit()
    auditor.run_full_audit()
    
    # Uncomment to export to CSV:
    # auditor.export_to_csv('dataset_audit_results.csv')
