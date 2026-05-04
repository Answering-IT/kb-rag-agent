#!/usr/bin/env python3
"""
Split large documents into smaller parts to avoid Bedrock KB metadata limit (2048 bytes).

Target: 8KB per part (generates ~2 Bedrock chunks, ~200 bytes metadata total)

Usage:
    python3 split-large-files.py --input documento.md --output ./chunks --max-size 8
    python3 split-large-files.py --input-dir ./docs --output-dir ./chunks --max-size 8
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def split_by_sections(content: str, max_size_kb: int) -> List[str]:
    """
    Split content by markdown sections (## headers) while respecting size limit.

    Args:
        content: Full document content
        max_size_kb: Maximum size per part in KB

    Returns:
        List of content parts
    """
    max_bytes = max_size_kb * 1024

    # Split by markdown headers
    lines = content.split('\n')
    sections = []
    current_section = []

    for line in lines:
        # Start new section on ## header (but not # or ###)
        if line.startswith('## ') and not line.startswith('### ') and current_section:
            sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    # Add last section
    if current_section:
        sections.append('\n'.join(current_section))

    # Combine sections into parts that fit size limit
    parts = []
    current_part_lines = []
    current_size = 0

    for section in sections:
        section_bytes = len(section.encode('utf-8'))

        # If single section is too large, split it further
        if section_bytes > max_bytes:
            # Save current part if exists
            if current_part_lines:
                parts.append('\n'.join(current_part_lines))
                current_part_lines = []
                current_size = 0

            # Split large section by paragraphs
            paragraphs = section.split('\n\n')
            for para in paragraphs:
                para_bytes = len(para.encode('utf-8'))

                if current_size + para_bytes > max_bytes:
                    if current_part_lines:
                        parts.append('\n\n'.join(current_part_lines))
                    current_part_lines = [para]
                    current_size = para_bytes
                else:
                    current_part_lines.append(para)
                    current_size += para_bytes

        # Regular section handling
        elif current_size + section_bytes > max_bytes:
            # Save current part and start new one
            if current_part_lines:
                parts.append('\n'.join(current_part_lines))
            current_part_lines = [section]
            current_size = section_bytes
        else:
            # Add to current part
            current_part_lines.append(section)
            current_size += section_bytes

    # Add final part
    if current_part_lines:
        parts.append('\n'.join(current_part_lines))

    return parts


def extract_metadata_from_file(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from .metadata.json file if exists.

    Args:
        file_path: Path to document file

    Returns:
        Metadata dict or empty dict
    """
    metadata_file = Path(str(file_path) + '.metadata.json')

    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_json = json.load(f)
                return metadata_json.get('metadataAttributes', {})
        except Exception as e:
            print(f"Warning: Could not read metadata from {metadata_file}: {e}")

    return {}


def save_part_with_metadata(
    part_content: str,
    output_path: Path,
    metadata: Dict[str, Any],
    part_num: int,
    total_parts: int,
    source_file: str
):
    """
    Save document part and its metadata file.

    Args:
        part_content: Content of this part
        output_path: Path to save the part
        metadata: Base metadata to include
        part_num: Part number (1-indexed)
        total_parts: Total number of parts
        source_file: Original filename
    """
    # Save content
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(part_content)

    # Enhance metadata with part info (optional, minimal)
    enhanced_metadata = metadata.copy()

    # Only add if not already present (keep metadata minimal)
    if 'source_document' not in enhanced_metadata:
        enhanced_metadata['source_document'] = source_file

    # Save metadata
    metadata_path = Path(str(output_path) + '.metadata.json')
    metadata_json = {
        "metadataAttributes": enhanced_metadata
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_json, f, indent=2)

    size_kb = len(part_content.encode('utf-8')) / 1024
    print(f"  ✅ Part {part_num}/{total_parts}: {output_path.name} ({size_kb:.1f} KB)")


def split_file(
    input_file: Path,
    output_dir: Path,
    max_size_kb: int,
    dry_run: bool = False
):
    """
    Split a single file into parts.

    Args:
        input_file: Input file path
        output_dir: Output directory
        max_size_kb: Max size per part in KB
        dry_run: If True, only show what would be done
    """
    print(f"\n📄 Processing: {input_file.name}")

    # Read file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return

    file_size_kb = len(content.encode('utf-8')) / 1024
    print(f"  Size: {file_size_kb:.1f} KB")

    # Check if splitting needed
    if file_size_kb <= max_size_kb:
        print(f"  ℹ️  File is small enough, no splitting needed")

        if not dry_run:
            # Copy as-is
            output_path = output_dir / input_file.name
            output_path.write_text(content, encoding='utf-8')

            # Copy metadata if exists
            metadata_file = Path(str(input_file) + '.metadata.json')
            if metadata_file.exists():
                output_metadata = output_dir / metadata_file.name
                output_metadata.write_text(
                    metadata_file.read_text(encoding='utf-8'),
                    encoding='utf-8'
                )
            print(f"  ✅ Copied to: {output_path.name}")

        return

    # Extract existing metadata
    metadata = extract_metadata_from_file(input_file)

    # Split content
    print(f"  🔪 Splitting into parts (max {max_size_kb} KB each)...")
    parts = split_by_sections(content, max_size_kb)

    print(f"  📦 Generated {len(parts)} parts")

    if dry_run:
        for i, part in enumerate(parts, 1):
            part_size_kb = len(part.encode('utf-8')) / 1024
            print(f"    Part {i}: {part_size_kb:.1f} KB")
        return

    # Save parts
    base_name = input_file.stem  # filename without extension
    ext = input_file.suffix

    for i, part in enumerate(parts, 1):
        part_filename = f"{base_name}_part{i}{ext}"
        part_path = output_dir / part_filename

        save_part_with_metadata(
            part,
            part_path,
            metadata,
            i,
            len(parts),
            input_file.name
        )


def process_directory(
    input_dir: Path,
    output_dir: Path,
    max_size_kb: int,
    extensions: List[str],
    dry_run: bool = False
):
    """
    Process all files in a directory.

    Args:
        input_dir: Input directory
        output_dir: Output directory
        max_size_kb: Max size per part in KB
        extensions: File extensions to process
        dry_run: If True, only show what would be done
    """
    # Find all files with matching extensions
    files = []
    for ext in extensions:
        files.extend(input_dir.glob(f"*{ext}"))

    # Exclude metadata files
    files = [f for f in files if not str(f).endswith('.metadata.json')]

    if not files:
        print(f"No files with extensions {extensions} found in {input_dir}")
        return

    print(f"\n📁 Processing {len(files)} files from {input_dir}")
    print(f"📂 Output directory: {output_dir}")
    print(f"📏 Max size per part: {max_size_kb} KB")

    if dry_run:
        print("\n🔍 DRY RUN - no files will be created\n")

    for file in files:
        split_file(file, output_dir, max_size_kb, dry_run)

    print(f"\n✅ Processing complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Split large documents for Bedrock KB metadata compliance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Split single file
  python3 split-large-files.py --input documento.md --output ./chunks

  # Split all markdown files in directory
  python3 split-large-files.py --input-dir ./docs --output-dir ./chunks

  # Dry run (preview only)
  python3 split-large-files.py --input documento.md --output ./chunks --dry-run

  # Custom max size (default 8KB)
  python3 split-large-files.py --input documento.md --output ./chunks --max-size 10
        '''
    )

    parser.add_argument('--input', type=str, help='Input file path')
    parser.add_argument('--input-dir', type=str, help='Input directory (processes all files)')
    parser.add_argument('--output', type=str, help='Output directory for single file')
    parser.add_argument('--output-dir', type=str, help='Output directory for directory processing')
    parser.add_argument('--max-size', type=int, default=8, help='Max size per part in KB (default: 8)')
    parser.add_argument('--extensions', nargs='+', default=['.md', '.txt'],
                       help='File extensions to process (default: .md .txt)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview only, do not create files')

    args = parser.parse_args()

    # Validate arguments
    if not args.input and not args.input_dir:
        parser.error("Either --input or --input-dir must be specified")

    if args.input and not args.output:
        parser.error("--output is required when using --input")

    if args.input_dir and not args.output_dir:
        parser.error("--output-dir is required when using --input-dir")

    # Process single file
    if args.input:
        input_file = Path(args.input)
        output_dir = Path(args.output)

        if not input_file.exists():
            print(f"Error: Input file not found: {input_file}")
            sys.exit(1)

        output_dir.mkdir(parents=True, exist_ok=True)

        split_file(input_file, output_dir, args.max_size, args.dry_run)

    # Process directory
    elif args.input_dir:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir)

        if not input_dir.exists():
            print(f"Error: Input directory not found: {input_dir}")
            sys.exit(1)

        output_dir.mkdir(parents=True, exist_ok=True)

        process_directory(input_dir, output_dir, args.max_size, args.extensions, args.dry_run)


if __name__ == '__main__':
    main()
