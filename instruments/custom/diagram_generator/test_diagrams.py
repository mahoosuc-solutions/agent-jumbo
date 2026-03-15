#!/usr/bin/env python3
"""
Test script for diagram generation capabilities
Demonstrates all three diagram types with various examples
"""

import os
import subprocess
import sys
from pathlib import Path


def run_test(name, command, expected_output):
    """Run a test and check if output file was created."""
    print(f"\n{'=' * 60}")
    print(f"TEST: {name}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            if os.path.exists(expected_output):
                size = os.path.getsize(expected_output)
                print(f"✅ SUCCESS - Created {expected_output} ({size} bytes)")
                return True
            else:
                print(f"❌ FAILED - File not created: {expected_output}")
                print(f"STDERR: {result.stderr}")
                return False
        else:
            print(f"❌ FAILED - Command failed with exit code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e!s}")
        return False


def main():
    print("=" * 60)
    print("AGENT ZERO - DIAGRAM GENERATION TEST SUITE")
    print("=" * 60)

    # Create test output directory
    test_dir = Path("/tmp/diagram_tests")  # nosec B108 - test output directory
    test_dir.mkdir(exist_ok=True)

    script_base = Path("/a0/instruments/custom/diagram_generator")

    results = []

    # ========================================
    # MERMAID TESTS
    # ========================================

    # Test 1: Simple flowchart
    results.append(
        run_test(
            "Mermaid - Simple Flowchart",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_flowchart.png"),
                "--code",
                "graph TD; A[Start]-->B[Process]-->C{Decision}; C-->|Yes|D[End]; C-->|No|B;",
            ],
            test_dir / "mermaid_flowchart.png",
        )
    )

    # Test 2: Sequence diagram
    results.append(
        run_test(
            "Mermaid - Sequence Diagram",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_sequence.png"),
                "--code",
                """sequenceDiagram
    participant User
    participant Agent
    participant Tool
    User->>Agent: Request
    Agent->>Tool: Execute
    Tool-->>Agent: Result
    Agent-->>User: Response""",
            ],
            test_dir / "mermaid_sequence.png",
        )
    )

    # Test 3: Class diagram
    results.append(
        run_test(
            "Mermaid - Class Diagram",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_class.png"),
                "--code",
                """classDiagram
    class Tool {
        +execute()
        +before_execution()
        +after_execution()
    }
    class DiagramTool {
        +generate_diagram()
    }
    Tool <|-- DiagramTool""",
            ],
            test_dir / "mermaid_class.png",
        )
    )

    # Test 4: State diagram
    results.append(
        run_test(
            "Mermaid - State Diagram",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_state.png"),
                "--code",
                """stateDiagram-v2
    [*] --> Idle
    Idle --> Processing: start
    Processing --> Success: complete
    Processing --> Error: fail
    Success --> [*]
    Error --> Idle: retry""",
            ],
            test_dir / "mermaid_state.png",
        )
    )

    # Test 5: ER diagram
    results.append(
        run_test(
            "Mermaid - ER Diagram",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_er.png"),
                "--code",
                """erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    PRODUCT ||--o{ LINE-ITEM : "ordered in" """,
            ],
            test_dir / "mermaid_er.png",
        )
    )

    # Test 6: Gantt chart
    results.append(
        run_test(
            "Mermaid - Gantt Chart",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_gantt.png"),
                "--code",
                """gantt
    title Project Timeline
    dateFormat YYYY-MM-DD
    section Phase 1
    Task 1: 2026-01-01, 30d
    Task 2: 2026-02-01, 20d""",
            ],
            test_dir / "mermaid_gantt.png",
        )
    )

    # Test 7: SVG output
    results.append(
        run_test(
            "Mermaid - SVG Format",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_flowchart.svg"),
                "--format",
                "svg",
                "--code",
                "graph LR; A-->B-->C;",
            ],
            test_dir / "mermaid_flowchart.svg",
        )
    )

    # Test 8: Dark theme
    results.append(
        run_test(
            "Mermaid - Dark Theme",
            [
                "python3",
                str(script_base / "generate_mermaid.py"),
                "--output",
                str(test_dir / "mermaid_dark.png"),
                "--theme",
                "dark",
                "--background",
                "transparent",
                "--code",
                "graph TB; A[Start]-->B[End];",
            ],
            test_dir / "mermaid_dark.png",
        )
    )

    # ========================================
    # EXCALIDRAW TESTS
    # ========================================

    # Test 9: Excalidraw flowchart template
    results.append(
        run_test(
            "Excalidraw - Flowchart Template",
            [
                "python3",
                str(script_base / "generate_excalidraw.py"),
                "--output",
                str(test_dir / "excalidraw_flowchart.excalidraw"),
                "--template",
                "flowchart",
            ],
            test_dir / "excalidraw_flowchart.excalidraw",
        )
    )

    # Test 10: Excalidraw custom elements
    results.append(
        run_test(
            "Excalidraw - Custom Elements",
            [
                "python3",
                str(script_base / "generate_excalidraw.py"),
                "--output",
                str(test_dir / "excalidraw_custom.excalidraw"),
                "--elements",
                '[{"type":"rectangle","x":100,"y":100,"width":200,"height":100,"text":"Hello Agent Zero"}]',
            ],
            test_dir / "excalidraw_custom.excalidraw",
        )
    )

    # ========================================
    # DRAW.IO TESTS
    # ========================================

    # Test 11: Draw.io flowchart template
    results.append(
        run_test(
            "Draw.io - Flowchart Template",
            [
                "python3",
                str(script_base / "generate_drawio.py"),
                "--output",
                str(test_dir / "drawio_flowchart.drawio"),
                "--template",
                "flowchart",
            ],
            test_dir / "drawio_flowchart.drawio",
        )
    )

    # Test 12: Draw.io network template
    results.append(
        run_test(
            "Draw.io - Network Template",
            [
                "python3",
                str(script_base / "generate_drawio.py"),
                "--output",
                str(test_dir / "drawio_network.drawio"),
                "--template",
                "network",
            ],
            test_dir / "drawio_network.drawio",
        )
    )

    # ========================================
    # SUMMARY
    # ========================================

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        print(f"\nGenerated files are in: {test_dir}")
        print("\nYou can view them:")
        print(f"  ls -lh {test_dir}")
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
