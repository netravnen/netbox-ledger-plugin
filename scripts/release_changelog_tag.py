#!/usr/bin/env python3
"""Validate changelog/version consistency and create annotated release tags.

This script keeps release tagging deterministic by extracting the exact version
entry from CHANGELOG.md and using it as the annotated tag message.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable

CHANGELOG_PATH = pathlib.Path('CHANGELOG.md')
VERSION_PATH = pathlib.Path('netbox_ledger_tracker/version.py')
PLUGIN_METADATA_PATH = pathlib.Path('netbox-plugin.yaml')

HEADING_RE = re.compile(
    r'^## (?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?) - '
    r'(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})$'
)
VERSION_RE = re.compile(r'^__version__\s*=\s*[\"\'](?P<version>[^\"\']+)[\"\']\s*$')


class ReleaseError(RuntimeError):
    """Raised when release tagging preconditions are not met."""


def _read_text(path: pathlib.Path) -> str:
    if not path.exists():
        raise ReleaseError(f'Required file not found: {path}')
    return path.read_text(encoding='utf-8')


def get_package_version() -> str:
    for line in _read_text(VERSION_PATH).splitlines():
        match = VERSION_RE.match(line.strip())
        if match:
            return match.group('version')
    raise ReleaseError(f'Could not parse __version__ from {VERSION_PATH}')


def get_latest_changelog_version() -> str:
    lines = _read_text(CHANGELOG_PATH).splitlines(keepends=True)
    headings = _iter_version_headings(lines)
    if not headings:
        raise ReleaseError(f'Could not find any release headings in {CHANGELOG_PATH}.')
    return headings[0][1]


def _iter_version_headings(lines: Iterable[str]) -> list[tuple[int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.rstrip('\n'))
        if match:
            headings.append((index, match.group('version'), match.group('date')))
    return headings


def extract_changelog_section(version: str) -> str:
    lines = _read_text(CHANGELOG_PATH).splitlines(keepends=True)
    headings = _iter_version_headings(lines)

    matches = [(idx, date) for idx, heading_version, date in headings if heading_version == version]
    if not matches:
        raise ReleaseError(f'No changelog section found for version {version} in {CHANGELOG_PATH}.')
    if len(matches) > 1:
        raise ReleaseError(f'Duplicate changelog headings found for version {version} in {CHANGELOG_PATH}.')

    start_idx, heading_date = matches[0]
    try:
        dt.date.fromisoformat(heading_date)
    except ValueError as exc:
        raise ReleaseError(f'Changelog heading for version {version} has invalid date: {heading_date}') from exc

    end_idx = len(lines)
    for idx, _, _ in headings:
        if idx > start_idx:
            end_idx = idx
            break

    section = ''.join(lines[start_idx:end_idx]).rstrip() + '\n'
    return section


def check_plugin_metadata_contains_release(version: str) -> None:
    text = _read_text(PLUGIN_METADATA_PATH)
    marker_re = re.compile(rf'^\s*-\s*release:\s*{re.escape(version)}\s*$', re.MULTILINE)
    if marker_re.search(text) is None:
        raise ReleaseError(f'{PLUGIN_METADATA_PATH} does not contain compatibility entry for release {version}.')


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', *args],
        check=False,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )


def tag_exists(tag_name: str) -> bool:
    result = run_git('rev-parse', '--verify', '--quiet', f'refs/tags/{tag_name}')
    return result.returncode == 0


def ensure_clean_worktree() -> None:
    result = run_git('status', '--porcelain')
    if result.returncode != 0:
        raise ReleaseError(f'Failed to inspect git worktree: {result.stderr.strip()}')
    if result.stdout.strip():
        raise ReleaseError('Working tree is not clean. Commit or stash changes before creating a release tag.')


def write_github_output(key: str, value: str) -> None:
    output_path = os.environ.get('GITHUB_OUTPUT')
    if not output_path:
        return
    with pathlib.Path(output_path).open('a', encoding='utf-8') as handle:
        handle.write(f'{key}={value}\n')


def resolve_version(explicit_version: str | None) -> str:
    return explicit_version or get_latest_changelog_version()


def get_literal_runtime_version() -> str | None:
    try:
        module = ast.parse(_read_text(VERSION_PATH), filename=str(VERSION_PATH))
    except SyntaxError as exc:
        raise ReleaseError(f'Could not parse {VERSION_PATH}: {exc}') from exc

    for statement in module.body:
        if not isinstance(statement, ast.Assign):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id == '__version__':
                if isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
                    return statement.value.value
                return None
    return None


def validate_release(
    version: str,
    require_compatibility_entry: bool,
    require_clean: bool,
    skip_version_check: bool = False,
) -> str:
    if not skip_version_check:
        package_version = get_literal_runtime_version()
        if package_version is not None and package_version != version:
            raise ReleaseError(
                f'Version mismatch: netbox_ledger_tracker/version.py is {package_version},'
                f' but target release is {version}.'
                f' Pass --skip-version-check to bypass this check for historical tags.'
            )

    section = extract_changelog_section(version)
    if require_compatibility_entry:
        check_plugin_metadata_contains_release(version)
    if require_clean:
        ensure_clean_worktree()
    return section


def cmd_print_version(_: argparse.Namespace) -> int:
    print(get_latest_changelog_version())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    version = resolve_version(args.version)
    section = validate_release(
        version=version,
        require_compatibility_entry=args.require_compatibility_entry,
        require_clean=args.require_clean,
        skip_version_check=args.skip_version_check,
    )
    tag_name = f'v{version}'

    if tag_exists(tag_name):
        raise ReleaseError(f'Tag already exists: {tag_name}')

    print(f'Validated release inputs for {tag_name}')
    write_github_output('version', version)
    write_github_output('tag', tag_name)
    write_github_output('changelog_heading', section.splitlines()[0])
    return 0


def cmd_write_tag_message(args: argparse.Namespace) -> int:
    version = resolve_version(args.version)
    section = validate_release(
        version=version,
        require_compatibility_entry=args.require_compatibility_entry,
        require_clean=args.require_clean,
        skip_version_check=args.skip_version_check,
    )

    destination = pathlib.Path(args.output)
    destination.write_text(section, encoding='utf-8')
    print(f'Wrote tag message to {destination}')

    write_github_output('version', version)
    write_github_output('tag', f'v{version}')
    write_github_output('tag_message_file', str(destination))
    return 0


def cmd_create_tag(args: argparse.Namespace) -> int:
    version = resolve_version(args.version)
    tag_name = f'v{version}'

    if tag_exists(tag_name) and not args.force:
        raise ReleaseError(f'Tag already exists: {tag_name}. Pass --force to delete and recreate it.')

    if args.message_file:
        message = pathlib.Path(args.message_file).read_text(encoding='utf-8')
    else:
        message = validate_release(
            version=version,
            require_compatibility_entry=args.require_compatibility_entry,
            require_clean=args.require_clean,
            skip_version_check=args.skip_version_check,
        )

    # Write message to a temp file and use -F --cleanup=verbatim so that lines
    # beginning with '#' (markdown headings) are preserved and never treated as
    # git comment lines (which happens when passing the message via -m).
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
        tmp.write(message)
        tmp_path = tmp.name

    try:
        git_tag_args = ['tag', '--cleanup=verbatim', '-a', tag_name, '-F', tmp_path]
        if args.force:
            git_tag_args.insert(2, '-f')
        if args.commit:
            git_tag_args.append(args.commit)

        tag_result = run_git(*git_tag_args)
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)
    if tag_result.returncode != 0:
        raise ReleaseError(f'Failed to create tag {tag_name}: {tag_result.stderr.strip()}')

    if args.push:
        push_result = run_git('push', args.remote, tag_name)
        if push_result.returncode != 0:
            raise ReleaseError(f'Failed to push tag {tag_name} to {args.remote}: {push_result.stderr.strip()}')

    print(f'Created annotated tag {tag_name}')
    if args.push:
        print(f'Pushed {tag_name} to {args.remote}')

    write_github_output('version', version)
    write_github_output('tag', tag_name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Validate changelog-based release inputs and create annotated tags.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    print_version = subparsers.add_parser('print-version', help='Print the latest changelog release version')
    print_version.set_defaults(func=cmd_print_version)

    validate = subparsers.add_parser('validate', help='Validate version/changelog state without creating a tag')
    validate.add_argument('--version', help='Release version (defaults to latest CHANGELOG heading)')
    validate.add_argument(
        '--require-compatibility-entry',
        action='store_true',
        help='Require netbox-plugin.yaml compatibility entry for target version',
    )
    validate.add_argument(
        '--require-clean',
        action='store_true',
        help='Require clean git worktree',
    )
    validate.add_argument(
        '--skip-version-check',
        action='store_true',
        help='Skip version.py literal consistency check (for historical/backfill tags)',
    )
    validate.set_defaults(func=cmd_validate)

    write_message = subparsers.add_parser(
        'write-tag-message',
        help='Write extracted changelog section to a file for later tag creation',
    )
    write_message.add_argument('--version', help='Release version (defaults to latest CHANGELOG heading)')
    write_message.add_argument('--output', required=True, help='Output file path')
    write_message.add_argument(
        '--require-compatibility-entry',
        action='store_true',
        help='Require netbox-plugin.yaml compatibility entry for target version',
    )
    write_message.add_argument(
        '--require-clean',
        action='store_true',
        help='Require clean git worktree',
    )
    write_message.add_argument(
        '--skip-version-check',
        action='store_true',
        help='Skip version.py literal consistency check (for historical/backfill tags)',
    )
    write_message.set_defaults(func=cmd_write_tag_message)

    create_tag = subparsers.add_parser(
        'create-tag',
        help='Create an annotated release tag using extracted changelog content',
    )
    create_tag.add_argument('--version', help='Release version (defaults to latest CHANGELOG heading)')
    create_tag.add_argument('--message-file', help='Path to pre-generated tag message file')
    create_tag.add_argument('--push', action='store_true', help='Push tag to remote')
    create_tag.add_argument('--remote', default='origin', help='Remote name for push')
    create_tag.add_argument(
        '--require-compatibility-entry',
        action='store_true',
        help='Require netbox-plugin.yaml compatibility entry for target version',
    )
    create_tag.add_argument(
        '--require-clean',
        action='store_true',
        help='Require clean git worktree',
    )
    create_tag.add_argument(
        '--skip-version-check',
        action='store_true',
        help='Skip version.py literal consistency check (for historical/backfill tags)',
    )
    create_tag.add_argument(
        '--force',
        '-f',
        action='store_true',
        help='Delete and recreate an existing tag (amend)',
    )
    create_tag.add_argument(
        '--commit',
        help='Commit/ref to tag instead of HEAD (for historical tags)',
    )
    create_tag.set_defaults(func=cmd_create_tag)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except ReleaseError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
