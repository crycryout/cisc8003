#!/usr/bin/env python3
"""Build reproducible, allowlisted Homework 1 code/report and result ZIPs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bundle(path, files, note):
    rows = []
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, source in sorted(files.items()):
            assert source.is_file(), source
            assert not any(part in ('.local', '__pycache__') for part in source.parts)
            data = source.read_bytes()
            entry = zipfile.ZipInfo(name, (2026, 11, 7, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
            rows.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    'scope': note, 'files': rows}
        entry = zipfile.ZipInfo('PACKAGE_MANIFEST.json', (2026, 11, 7, 0, 0, 0))
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for row in rows:
            assert hashlib.sha256(archive.read(row['file'])).hexdigest() == row['sha256']
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path), 'members': len(rows) + 1}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, help='bonus-YYYYMMDDTHHMMSSZ')
    p.add_argument('--output-dir', type=Path, required=True, help='New local delivery directory')
    a = p.parse_args()
    if not a.run.startswith('bonus-') or '/' in a.run or '..' in a.run:
        p.error('Invalid run ID')
    a.output_dir.mkdir(parents=True, exist_ok=False)
    files = {'START_HERE.md': ROOT / 'docs/CODE_PACKAGE.md'}
    for folder in ('homework1/src', 'homework1/cluster', 'homework1/tests'):
        for source in (ROOT / folder).rglob('*'):
            if source.is_file() and source.suffix in ('.py', '.sh', '.md', '.xml', '.txt') and '__pycache__' not in source.parts:
                files[str(source.relative_to(ROOT))] = source
    for name in ('README.md', 'docs/FINAL_SUBMISSION.md', 'docs/LAB_EXECUTION.md',
                 'docs/EVIDENCE_INDEX.md', 'docs/ASSIGNMENT_REQUIREMENTS.md',
                 'scripts/compare_top10.py', 'homework1/report/Homework1_Report.pdf',
                 'homework1/report/Homework1_Report_Draft.md', 'homework1/report/build_report.py',
                 'homework1/data/figure_numeric.txt', 'homework1/data/hadoop_regression.txt'):
        files[name] = ROOT / name
    files['REPOSITORY_README.md'] = ROOT / 'README.md'
    files['README.md'] = ROOT / 'docs/CODE_PACKAGE.md'
    for run in ('lab-20261106T110350Z', 'lab-' + a.run):
        for source in (ROOT / 'homework1/evidence' / run).rglob('*'):
            if source.is_file():
                files[str(source.relative_to(ROOT))] = source
    records = [bundle(a.output_dir / 'Homework1_Code_Report.zip', files,
                      'Code, editable report, final PDF and public redacted evidence; no raw course datasets or access configuration.')]
    artifacts = ROOT / 'homework1/artifacts'
    names = ['medium_all_users_top10_lab-20261106T110350Z.txt.gz',
             'medium_by_suffix_lab-20261106T110350Z.tar.gz',
             'large_all_users_top10_lab-' + a.run + '.txt.gz',
             'large_by_suffix_lab-' + a.run + '.tar.gz']
    results = {name: artifacts / name for name in names}
    for name in ('suffix-manifest.json', 'output-manifest.json', 'validation.json'):
        results['large/' + name] = ROOT / 'homework1/evidence' / ('lab-' + a.run) / name
    results['STUDENT_ACTIONS.md'] = ROOT / 'docs/FINAL_SUBMISSION.md'
    records.append(bundle(a.output_dir / 'Homework1_Results.zip', results,
                          'Complete medium/large outputs and all 000-999 suffixes; student selects their suffix after checking course submission requirements.'))
    (a.output_dir / 'DELIVERY_MANIFEST.json').write_text(json.dumps({'packages': records}, indent=2) + '\n')
    (a.output_dir / 'SHA256SUMS').write_text(''.join(row['sha256'] + '  ' + row['file'] + '\n' for row in records))
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
