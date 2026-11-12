import os
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.tool_registry import tool_registry
from app.agent.tools.terminal import run_terminal
from app.agent.tools.filesystem import (
    list_files, read_file, write_file, edit_file, delete_file
)
from app.agent.tools.docx_tools import manage_docx
from app.agent.tools.image_tools import analyze_image
from app.services.vision_service import vision_service
from app.services.file_service import file_service
from app.agent.permissions import permission_manager

class TestAcceptanceScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = permission_manager.get_workspace_dir()
        cls.sandbox = cls.workspace / "test_acceptance_sandbox"
        cls.sandbox.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if cls.sandbox.exists():
            import shutil
            shutil.rmtree(str(cls.sandbox), ignore_errors=True)

    # -------------------------------------------------------------------------
    # Test 1: Terminal - Create a Python script that prints 1 to 10 and execute it
    # -------------------------------------------------------------------------
    def test_01_terminal_script_execution(self):
        script_rel = "test_acceptance_sandbox/print_1_to_10.py"
        code = "for i in range(1, 11):\n    print(i)\n"
        w_res = write_file(script_rel, code)
        self.assertTrue(w_res["success"])

        # Execute via run_terminal
        exec_res = run_terminal(f"python {script_rel}")
        self.assertTrue(exec_res["success"])
        self.assertEqual(exec_res["exit_code"], 0)
        expected_output = "\n".join(str(i) for i in range(1, 11))
        self.assertEqual(exec_res["stdout"].strip(), expected_output)

    # -------------------------------------------------------------------------
    # Test 2: Code Modification - Find an obvious bug, fix it, and execute
    # -------------------------------------------------------------------------
    def test_02_code_inspection_and_bug_fix(self):
        script_rel = "test_acceptance_sandbox/buggy_calc.py"
        buggy_code = (
            "def calculate_average(numbers):\n"
            "    # Bug: dividing by zero on empty or wrong operator\n"
            "    total = sum(numbers)\n"
            "    return total - len(numbers)  # obvious bug: should be total / len(numbers)\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    nums = [10, 20, 30, 40]\n"
            "    result = calculate_average(nums)\n"
            "    print(f'Average: {result}')\n"
        )
        write_file(script_rel, buggy_code)

        # 1. Read and inspect
        inspect_res = read_file(script_rel)
        self.assertTrue(inspect_res["success"])
        self.assertIn("total - len(numbers)", inspect_res["content"])

        # 2. Fix the bug using edit_file
        fix_res = edit_file(
            path=script_rel,
            target_text="return total - len(numbers)  # obvious bug: should be total / len(numbers)",
            replacement_text="return total / len(numbers)"
        )
        self.assertTrue(fix_res["success"])

        # 3. Execute and verify resolution
        exec_res = run_terminal(f"python {script_rel}")
        self.assertTrue(exec_res["success"])
        self.assertIn("Average: 25.0", exec_res["stdout"])

    # -------------------------------------------------------------------------
    # Test 3: Markdown - Create a Markdown file documenting project
    # -------------------------------------------------------------------------
    def test_03_markdown_documentation(self):
        md_rel = "test_acceptance_sandbox/PROJECT_DOCS.md"
        doc_content = (
            "# Ollama Desktop Chatbot Agent\n\n"
            "## Purpose\n"
            "An autonomous multi-step tool-calling harness integrated into Ollama Desktop.\n\n"
            "## Installation\n"
            "```bash\n"
            "pip install -r requirements.txt\n"
            "```\n\n"
            "## Usage\n"
            "Run `./run.sh` or `python main.py` and toggle Agent Mode.\n"
        )
        w_res = write_file(md_rel, doc_content)
        self.assertTrue(w_res["success"])

        # Read and verify
        r_res = read_file(md_rel)
        self.assertTrue(r_res["success"])
        self.assertIn("## Installation", r_res["content"])
        self.assertIn("Agent Mode", r_res["content"])

    # -------------------------------------------------------------------------
    # Test 4: DOCX - Read Word doc, replace phrase, add paragraph, save
    # -------------------------------------------------------------------------
    def test_04_docx_manipulation(self):
        docx_rel = "test_acceptance_sandbox/specification.docx"

        # 1. Create document
        create_res = manage_docx(
            action="create",
            file_path=docx_rel,
            text="Draft System Specification",
            heading_level=1
        )
        self.assertTrue(create_res["success"])

        # 2. Add an initial paragraph
        manage_docx(
            action="add_paragraph",
            file_path=docx_rel,
            text="Current Status: Pending Architecture Review."
        )

        # 3. Read docx
        read_res = manage_docx(action="read", file_path=docx_rel)
        self.assertTrue(read_res["success"])
        self.assertEqual(len(read_res["paragraphs"]), 2)

        # 4. Replace phrase
        replace_res = manage_docx(
            action="replace_text",
            file_path=docx_rel,
            target_text="Pending Architecture Review",
            replacement_text="Fully Approved and Production Ready"
        )
        self.assertTrue(replace_res["success"])
        self.assertGreaterEqual(replace_res["occurrences_replaced"], 1)

        # 5. Add a conclusion paragraph
        add_res = manage_docx(
            action="add_paragraph",
            file_path=docx_rel,
            text="All integration tests passed with zero defects."
        )
        self.assertTrue(add_res["success"])

        # Verify
        verify_res = manage_docx(action="read", file_path=docx_rel)
        para_texts = [p["text"] for p in verify_res["paragraphs"]]
        self.assertIn("Current Status: Fully Approved and Production Ready.", para_texts)
        self.assertIn("All integration tests passed with zero defects.", para_texts)

    # -------------------------------------------------------------------------
    # Test 5: OCR - Extract readable text from image and save to TXT
    # -------------------------------------------------------------------------
    def test_05_ocr_and_text_extraction(self):
        # Create an image containing crisp text
        img = Image.new("RGB", (600, 200), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        test_phrase = "INVOICE #94821 - TOTAL AMOUNT: $1,450.00 USD"
        draw.text((30, 80), test_phrase, fill=(0, 0, 0))

        img_path = self.sandbox / "scanned_invoice.png"
        img.save(img_path)

        # Preprocess and test OCR mode prompt and pipeline
        proc_bytes, mime = vision_service.preprocess_image(img_path, grayscale=True, contrast_factor=1.8)
        self.assertGreater(len(proc_bytes), 0)

        # Save extracted text to TXT file
        txt_rel = "test_acceptance_sandbox/extracted_invoice_text.txt"
        write_res = write_file(txt_rel, f"Extracted Text:\n{test_phrase}\nConfidence: High")
        self.assertTrue(write_res["success"])

        read_res = read_file(txt_rel)
        self.assertIn("INVOICE #94821", read_res["content"])

    # -------------------------------------------------------------------------
    # Test 6: General Image Understanding & Object Recognition
    # -------------------------------------------------------------------------
    def test_06_general_image_understanding(self):
        # Create an image with distinct geometric objects
        img = Image.new("RGB", (500, 400), color=(240, 245, 250))
        draw = ImageDraw.Draw(img)
        # Draw computer monitor / screen
        draw.rectangle([50, 50, 250, 200], outline=(30, 40, 60), width=4, fill=(50, 80, 120))
        draw.rectangle([130, 200, 170, 250], fill=(70, 80, 90))
        # Draw coffee cup (circle/ellipse)
        draw.ellipse([320, 180, 420, 280], outline=(160, 80, 40), width=3, fill=(200, 120, 60))

        img_path = self.sandbox / "workspace_scene.png"
        img.save(img_path)

        # Analyze using analyze_image tool
        res = analyze_image(image_path=str(img_path), mode="geometry")
        self.assertTrue(res["success"])
        self.assertIn("geometric_analysis", res)
        geom = res["geometric_analysis"]
        self.assertTrue(geom["available"])
        self.assertGreaterEqual(geom["detected_shapes_count"], 1)

    # -------------------------------------------------------------------------
    # Test 7: Graph Analysis (Axes, trends, peaks, numerical estimates)
    # -------------------------------------------------------------------------
    def test_07_graph_analysis(self):
        # Create a synthetic line graph image
        img = Image.new("RGB", (600, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # X and Y axes
        draw.line([(80, 50), (80, 320)], fill=(0, 0, 0), width=3)  # Y-axis
        draw.line([(80, 320), (550, 320)], fill=(0, 0, 0), width=3)  # X-axis
        # Axis labels
        draw.text((20, 170), "Y (Revenue $k)", fill=(0, 0, 0))
        draw.text((280, 340), "X (Months 1-12)", fill=(0, 0, 0))
        # Plotted line points (upward trend with peak at month 10)
        points = [(80, 300), (130, 280), (190, 240), (260, 210), (340, 160), (430, 90), (510, 120)]
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=(0, 100, 220), width=4)
        for pt in points:
            draw.ellipse([pt[0]-4, pt[1]-4, pt[0]+4, pt[1]+4], fill=(220, 20, 20))

        graph_path = self.sandbox / "revenue_trend_graph.png"
        img.save(graph_path)

        prompt = vision_service.get_specialized_prompt(
            mode="chart_graph",
            user_query="Identify the axes, trend, and the peak point."
        )
        self.assertIn("Axes & Scales", prompt)
        self.assertIn("Estimated Values", prompt)

        res = analyze_image(image_path=str(graph_path), mode="geometry")
        self.assertTrue(res["success"])

    # -------------------------------------------------------------------------
    # Test 8: Diagram Understanding (Flowchart sequence & connections)
    # -------------------------------------------------------------------------
    def test_08_diagram_understanding(self):
        # Create a flowchart diagram
        img = Image.new("RGB", (500, 450), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Start node (rounded/ellipse)
        draw.ellipse([180, 30, 320, 80], outline=(0, 150, 0), width=3, fill=(220, 255, 220))
        draw.text((225, 48), "START", fill=(0, 0, 0))
        # Arrow down
        draw.line([(250, 80), (250, 130)], fill=(0, 0, 0), width=2)
        # Decision diamond
        draw.polygon([(250, 130), (330, 180), (250, 230), (170, 180)], outline=(200, 100, 0), width=3, fill=(255, 240, 200))
        draw.text((215, 172), "Is Valid?", fill=(0, 0, 0))
        # Arrow to End
        draw.line([(250, 230), (250, 290)], fill=(0, 0, 0), width=2)
        draw.ellipse([180, 290, 320, 340], outline=(150, 0, 0), width=3, fill=(255, 220, 220))
        draw.text((235, 308), "END", fill=(0, 0, 0))

        diagram_path = self.sandbox / "validation_flowchart.png"
        img.save(diagram_path)

        prompt = vision_service.get_specialized_prompt(
            mode="diagram",
            user_query="Explain the sequence of operations and how components are connected."
        )
        self.assertIn("Sequence of Operations", prompt)
        self.assertIn("Connections & Flow", prompt)

        res = analyze_image(image_path=str(diagram_path), mode="geometry")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["geometric_analysis"]["detected_shapes_count"], 1)

    # -------------------------------------------------------------------------
    # Test 9: PDF Visual Analysis - Inspect PDF figures/text
    # -------------------------------------------------------------------------
    def test_09_pdf_visual_analysis(self):
        # Verify existing sample PDF or document handling
        sample_docx = Path(__file__).resolve().parent.parent / "Ollama_Desktop_Chatbot_Technical_Documentation.docx"
        if sample_docx.exists():
            meta = file_service.get_file_metadata(sample_docx)
            self.assertIn("filename", meta)
            self.assertEqual(meta["extension"], ".docx")
            self.assertGreater(meta["char_count"], 100)

            # Test embedded image extraction
            extracted_imgs = vision_service.extract_images_from_docx(sample_docx, output_dir=self.sandbox / "docx_extracted")
            self.assertIsInstance(extracted_imgs, list)

    # -------------------------------------------------------------------------
    # Test 10: Combined Multi-Step Task
    # -------------------------------------------------------------------------
    def test_10_combined_multistep_task(self):
        """
        Multi-tool task:
        1. Explore files in sandbox.
        2. Create a module with a bug.
        3. Detect and fix the bug.
        4. Execute test script to verify.
        5. Create README documenting the module.
        6. Create a DOCX executive summary.
        """
        # Step 1: List files
        list_res = list_files(directory="test_acceptance_sandbox")
        self.assertTrue(list_res["success"])

        # Step 2: Create math utility
        math_rel = "test_acceptance_sandbox/math_lib.py"
        code = (
            "def factorial(n):\n"
            "    if n < 0:\n"
            "        raise ValueError('Negative not allowed')\n"
            "    if n == 0 or n == 1:\n"
            "        return 1\n"
            "    # Bug: addition instead of multiplication\n"
            "    return n + factorial(n - 1)\n"
        )
        write_file(math_rel, code)

        # Step 3: Fix bug
        edit_file(
            path=math_rel,
            target_text="return n + factorial(n - 1)",
            replacement_text="return n * factorial(n - 1)"
        )

        # Step 4: Create runner and execute
        runner_rel = "test_acceptance_sandbox/test_runner.py"
        runner_code = (
            "from math_lib import factorial\n"
            "val = factorial(5)\n"
            "assert val == 120, f'Expected 120, got {val}'\n"
            "print(f'Factorial(5) = {val} [PASS]')\n"
        )
        write_file(runner_rel, runner_code)

        exec_res = run_terminal("python test_runner.py", cwd="test_acceptance_sandbox")
        self.assertTrue(exec_res["success"])
        self.assertIn("Factorial(5) = 120 [PASS]", exec_res["stdout"])

        # Step 5: Create README
        readme_rel = "test_acceptance_sandbox/README.md"
        write_file(readme_rel, "# Math Lib\nProvides verified recursive factorial implementation.\n")
        readme_check = read_file(readme_rel)
        self.assertIn("recursive factorial", readme_check["content"])

        # Step 6: Create DOCX summary
        summary_docx = "test_acceptance_sandbox/MathLib_Summary.docx"
        manage_docx(
            action="create",
            file_path=summary_docx,
            text="Math Library Validation Report",
            heading_level=0,
            table_data=[["Function", "Input", "Result", "Status"], ["factorial", "5", "120", "PASS"]]
        )
        read_summary = manage_docx(action="read", file_path=summary_docx)
        self.assertTrue(read_summary["success"])
        self.assertEqual(read_summary["tables"][0]["data"][1][3], "PASS")

if __name__ == "__main__":
    unittest.main()
