#!/usr/bin/env python3
"""
Mermaid Diagram Generator
Converts Mermaid syntax to PNG/SVG images using mermaid-cli (mmdc)
"""

import argparse
import os
import subprocess
import sys
import tempfile


def generate_mermaid_diagram(
    mermaid_code: str,
    output_path: str,
    format: str = "png",
    theme: str = "default",
    background: str = "white",
    width: int = 1920,
    height: int = 1080,
):
    """
    Generate a diagram from Mermaid code.

    Args:
        mermaid_code: Mermaid diagram syntax
        output_path: Path to save the output file
        format: Output format (png, svg, pdf)
        theme: Mermaid theme (default, dark, forest, neutral)
        background: Background color
        width: Output width in pixels
        height: Output height in pixels
    """
    # Create temp file for mermaid code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
        f.write(mermaid_code)
        temp_input = f.name

    try:
        # Check if mmdc (mermaid-cli) is available
        try:
            subprocess.run(["mmdc", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try to install mermaid-cli if not available
            print("Installing @mermaid-js/mermaid-cli...", file=sys.stderr)
            subprocess.run(["npm", "install", "-g", "@mermaid-js/mermaid-cli"], check=True)

        # Generate diagram
        cmd = [
            "mmdc",
            "-i",
            temp_input,
            "-o",
            output_path,
            "-t",
            theme,
            "-b",
            background,
            "-w",
            str(width),
            "-H",
            str(height),
        ]

        if format == "svg":
            cmd.extend(["-f", "svg"])
        elif format == "pdf":
            cmd.extend(["-f", "pdf"])
        else:  # default to png
            cmd.extend(["-f", "png"])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error generating diagram: {result.stderr}", file=sys.stderr)
            return False

        print(f"Successfully generated diagram: {output_path}")
        return True

    except Exception as e:
        print(f"Error: {e!s}", file=sys.stderr)
        return False
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_input)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate diagrams from Mermaid syntax",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a flowchart
  python generate_mermaid.py --output diagram.png --code "graph TD; A-->B;"

  # Generate from file
  python generate_mermaid.py --output diagram.svg --format svg --input diagram.mmd

  # With custom theme
  python generate_mermaid.py --output diagram.png --theme dark --code "flowchart LR; Start-->End"
        """,
    )

    parser.add_argument("--output", "-o", required=True, help="Output file path (e.g., diagram.png)")
    parser.add_argument("--code", "-c", help="Mermaid diagram code (inline)")
    parser.add_argument("--input", "-i", help="Input file containing Mermaid code")
    parser.add_argument(
        "--format", "-f", choices=["png", "svg", "pdf"], default="png", help="Output format (default: png)"
    )
    parser.add_argument(
        "--theme", "-t", choices=["default", "dark", "forest", "neutral"], default="default", help="Diagram theme"
    )
    parser.add_argument("--background", "-b", default="white", help="Background color (default: white)")
    parser.add_argument("--width", "-w", type=int, default=1920, help="Output width in pixels (default: 1920)")
    parser.add_argument("--height", "-H", type=int, default=1080, help="Output height in pixels (default: 1080)")

    args = parser.parse_args()

    # Get mermaid code from input file or inline
    if args.code:
        mermaid_code = args.code
    elif args.input:
        with open(args.input) as f:
            mermaid_code = f.read()
    else:
        print("Error: Must provide either --code or --input", file=sys.stderr)
        sys.exit(1)

    # Generate diagram
    success = generate_mermaid_diagram(
        mermaid_code=mermaid_code,
        output_path=args.output,
        format=args.format,
        theme=args.theme,
        background=args.background,
        width=args.width,
        height=args.height,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
