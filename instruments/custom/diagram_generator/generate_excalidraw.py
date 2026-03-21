#!/usr/bin/env python3
"""
Excalidraw Diagram Generator
Creates hand-drawn style diagrams using Excalidraw format
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from typing import Any


def create_excalidraw_element(
    element_type: str, x: int, y: int, width: int = 100, height: int = 100, text: str = "", **kwargs
) -> dict[str, Any]:
    """Create an Excalidraw element."""
    import random
    import time

    element_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    base_element = {
        "id": element_id,
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": kwargs.get("strokeColor", "#000000"),
        "backgroundColor": kwargs.get("backgroundColor", "transparent"),
        "fillStyle": kwargs.get("fillStyle", "hachure"),
        "strokeWidth": kwargs.get("strokeWidth", 1),
        "strokeStyle": kwargs.get("strokeStyle", "solid"),
        "roughness": kwargs.get("roughness", 1),
        "opacity": kwargs.get("opacity", 100),
        "groupIds": [],
        "roundness": None,
        "seed": random.randint(1, 2147483647),
        "version": 1,
        "versionNonce": random.randint(1, 2147483647),
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }

    if element_type in ["rectangle", "diamond", "ellipse"]:
        base_element["text"] = text
        if element_type == "diamond" or element_type == "ellipse":
            base_element["roundness"] = {"type": 2}
    elif element_type == "arrow" or element_type == "line":
        base_element["points"] = kwargs.get("points", [[0, 0], [width, height]])
        base_element["lastCommittedPoint"] = None
        base_element["startBinding"] = None
        base_element["endBinding"] = None
        base_element["startArrowhead"] = kwargs.get("startArrowhead")
        base_element["endArrowhead"] = kwargs.get("endArrowhead", "arrow")
    elif element_type == "text":
        base_element["text"] = text
        base_element["fontSize"] = kwargs.get("fontSize", 20)
        base_element["fontFamily"] = kwargs.get("fontFamily", 1)
        base_element["textAlign"] = kwargs.get("textAlign", "left")
        base_element["verticalAlign"] = kwargs.get("verticalAlign", "top")
        base_element["baseline"] = 18

    return base_element


def generate_excalidraw_diagram(elements: list[dict], output_path: str, format: str = "png", **kwargs):
    """
    Generate an Excalidraw diagram.

    Args:
        elements: List of Excalidraw elements
        output_path: Path to save the output
        format: Output format (json, png, svg)
    """
    # Create Excalidraw file structure
    excalidraw_data = {
        "type": "excalidraw",
        "version": 2,
        "source": "agent-jumbo",
        "elements": elements,
        "appState": {
            "gridSize": kwargs.get("gridSize"),
            "viewBackgroundColor": kwargs.get("viewBackgroundColor", "#ffffff"),
        },
        "files": {},
    }

    # If JSON output, just save the file
    if format == "json" or output_path.endswith(".excalidraw"):
        with open(output_path, "w") as f:
            json.dump(excalidraw_data, f, indent=2)
        print(f"Successfully generated Excalidraw file: {output_path}")
        return True

    # For image output, need to use excalidraw-cli or similar
    # Save JSON first
    with tempfile.NamedTemporaryFile(mode="w", suffix=".excalidraw", delete=False) as f:
        json.dump(excalidraw_data, f, indent=2)
        temp_file = f.name

    try:
        # Try using @excalidraw/cli if available
        # Note: This might need puppeteer or a headless browser
        try:
            # Check if excalidraw CLI is available
            subprocess.run(["excalidraw", "--version"], capture_output=True, check=True)

            cmd = ["excalidraw", temp_file, "-o", output_path]
            if format == "svg":
                cmd.append("--svg")

            subprocess.run(cmd, check=True)
            print(f"Successfully generated diagram: {output_path}")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: Save as JSON and inform user
            json_output = output_path.rsplit(".", 1)[0] + ".excalidraw"
            with open(json_output, "w") as f:
                json.dump(excalidraw_data, f, indent=2)
            print(f"Excalidraw CLI not available. Saved as JSON: {json_output}")
            print("You can open this file at https://excalidraw.com")
            return True

    except Exception as e:
        print(f"Error: {e!s}", file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate Excalidraw diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a simple rectangle
  python generate_excalidraw.py --output diagram.excalidraw \\
    --elements '[{"type":"rectangle","x":100,"y":100,"width":200,"height":100,"text":"Hello"}]'

  # Generate from template
  python generate_excalidraw.py --output diagram.png --template flowchart
        """,
    )

    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--elements", "-e", help="JSON array of Excalidraw elements")
    parser.add_argument(
        "--template", "-t", choices=["flowchart", "sequence", "architecture"], help="Use a predefined template"
    )
    parser.add_argument("--format", "-f", choices=["json", "png", "svg"], default="json", help="Output format")

    args = parser.parse_args()

    # Parse elements or use template
    if args.elements:
        elements = json.loads(args.elements)
    elif args.template:
        # Create template-based diagrams
        if args.template == "flowchart":
            elements = [
                create_excalidraw_element("rectangle", 100, 100, 200, 100, "Start"),
                create_excalidraw_element("arrow", 200, 200, 0, 100),
                create_excalidraw_element("diamond", 100, 350, 200, 150, "Decision"),
                create_excalidraw_element("arrow", 200, 500, 100, 0),
                create_excalidraw_element("rectangle", 100, 550, 200, 100, "End"),
            ]
        else:
            print(f"Template '{args.template}' not yet implemented", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Must provide either --elements or --template", file=sys.stderr)
        sys.exit(1)

    # Generate diagram
    success = generate_excalidraw_diagram(elements=elements, output_path=args.output, format=args.format)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
