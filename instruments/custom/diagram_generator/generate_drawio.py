#!/usr/bin/env python3
"""
Draw.io (diagrams.net) Diagram Generator
Creates professional technical diagrams using Draw.io XML format
"""

import argparse
import os
import subprocess
import sys
import tempfile


def create_drawio_xml(cells: list, **kwargs) -> str:
    """
    Create Draw.io XML from cell definitions.

    Args:
        cells: List of cell dictionaries with properties
        kwargs: Additional diagram properties

    Returns:
        Draw.io XML string
    """
    # Base XML structure
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="agent-jumbo" modified="{modified}" agent="Agent Jumbo" version="1.0" type="device">
  <diagram name="Diagram" id="diagram1">
    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

    import time

    modified_time = str(int(time.time() * 1000))

    # Generate cell XML
    cell_xml = []
    for i, cell in enumerate(cells, start=2):
        cell_id = cell.get("id", f"cell_{i}")
        cell_type = cell.get("type", "rectangle")
        value = cell.get("value", "")
        x = cell.get("x", 0)
        y = cell.get("y", 0)
        width = cell.get("width", 120)
        height = cell.get("height", 60)
        style = cell.get("style", "rounded=0;whiteSpace=wrap;html=1;")
        parent = cell.get("parent", "1")

        if cell_type == "edge":
            # Edge/Arrow
            source = cell.get("source", "")
            target = cell.get("target", "")
            cell_xml.append(
                f'        <mxCell id="{cell_id}" value="{value}" style="{style}" edge="1" parent="{parent}" source="{source}" target="{target}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
        else:
            # Vertex (rectangle, ellipse, etc.)
            cell_xml.append(
                f'        <mxCell id="{cell_id}" value="{value}" style="{style}" vertex="1" parent="{parent}">'
                f'<mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry"/></mxCell>'
            )

    return xml_template.format(modified=modified_time, cells="\n".join(cell_xml))


def generate_drawio_diagram(xml_content: str, output_path: str, format: str = "png"):
    """
    Generate a Draw.io diagram from XML.

    Args:
        xml_content: Draw.io XML content
        output_path: Path to save the output
        format: Output format (xml, png, svg, pdf)
    """
    # If XML output, just save the file
    if format == "xml" or output_path.endswith(".drawio") or output_path.endswith(".xml"):
        with open(output_path, "w") as f:
            f.write(xml_content)
        print(f"Successfully generated Draw.io file: {output_path}")
        return True

    # For image export, need draw.io CLI
    with tempfile.NamedTemporaryFile(mode="w", suffix=".drawio", delete=False) as f:
        f.write(xml_content)
        temp_file = f.name

    try:
        # Try using draw.io CLI (drawio)
        try:
            # Check if drawio is available
            subprocess.run(["drawio", "--version"], capture_output=True, check=True)

            cmd = ["drawio", "--export", "--format", format, "--output", output_path, temp_file]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"Draw.io export failed: {result.stderr}")

            print(f"Successfully generated diagram: {output_path}")
            return True

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: Save as XML
            xml_output = output_path.rsplit(".", 1)[0] + ".drawio"
            with open(xml_output, "w") as f:
                f.write(xml_content)
            print(f"Draw.io CLI not available. Saved as XML: {xml_output}")
            print("You can open this file at https://app.diagrams.net")
            return True

    except Exception as e:
        print(f"Error: {e!s}", file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(temp_file)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate Draw.io diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from XML string
  python generate_drawio.py --output diagram.png --xml "<mxfile>...</mxfile>"

  # Generate from template
  python generate_drawio.py --output diagram.drawio --template network
        """,
    )

    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--xml", "-x", help="Draw.io XML content (inline)")
    parser.add_argument("--input", "-i", help="Input file containing Draw.io XML")
    parser.add_argument(
        "--template",
        "-t",
        choices=["flowchart", "network", "architecture", "sequence"],
        help="Use a predefined template",
    )
    parser.add_argument("--format", "-f", choices=["xml", "png", "svg", "pdf"], default="png", help="Output format")

    args = parser.parse_args()

    # Get XML content
    if args.xml:
        xml_content = args.xml
    elif args.input:
        with open(args.input) as f:
            xml_content = f.read()
    elif args.template:
        # Create template-based diagrams
        if args.template == "flowchart":
            cells = [
                {
                    "id": "start",
                    "value": "Start",
                    "x": 340,
                    "y": 50,
                    "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
                },
                {
                    "id": "process",
                    "value": "Process",
                    "x": 340,
                    "y": 150,
                    "style": "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
                },
                {
                    "id": "decision",
                    "value": "Decision?",
                    "x": 340,
                    "y": 250,
                    "style": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;",
                },
                {
                    "id": "end",
                    "value": "End",
                    "x": 340,
                    "y": 370,
                    "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;",
                },
                {
                    "type": "edge",
                    "source": "start",
                    "target": "process",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
                },
                {
                    "type": "edge",
                    "source": "process",
                    "target": "decision",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
                },
                {
                    "type": "edge",
                    "source": "decision",
                    "target": "end",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
                },
            ]
            xml_content = create_drawio_xml(cells)
        elif args.template == "network":
            cells = [
                {
                    "id": "server",
                    "value": "Server",
                    "x": 200,
                    "y": 100,
                    "style": "shape=cube;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;darkOpacity=0.05;darkOpacity2=0.1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
                },
                {
                    "id": "client1",
                    "value": "Client 1",
                    "x": 100,
                    "y": 250,
                    "style": "rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
                },
                {
                    "id": "client2",
                    "value": "Client 2",
                    "x": 300,
                    "y": 250,
                    "style": "rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;",
                },
                {
                    "type": "edge",
                    "source": "server",
                    "target": "client1",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
                },
                {
                    "type": "edge",
                    "source": "server",
                    "target": "client2",
                    "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;",
                },
            ]
            xml_content = create_drawio_xml(cells)
        else:
            print(f"Template '{args.template}' not yet implemented", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Must provide --xml, --input, or --template", file=sys.stderr)
        sys.exit(1)

    # Generate diagram
    success = generate_drawio_diagram(xml_content=xml_content, output_path=args.output, format=args.format)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
