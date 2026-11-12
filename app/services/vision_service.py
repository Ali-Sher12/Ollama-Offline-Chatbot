import io
import os
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from PIL import Image, ImageOps, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Check if cv2 and numpy are available
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class VisionService:
    """
    Multimodal visual understanding, OCR, chart analysis, diagram interpretation,
    and image preprocessing (Pillow & OpenCV).
    """

    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # Image Preprocessing (Pillow & OpenCV)
    # -------------------------------------------------------------------------
    def preprocess_image(
        self,
        image_input: Union[str, Path, bytes, Image.Image],
        resize_max: Tuple[int, int] = (1600, 1600),
        grayscale: bool = False,
        contrast_factor: Optional[float] = None,
        brightness_factor: Optional[float] = None,
        rotate_deg: int = 0,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
        output_format: str = "PNG"
    ) -> Tuple[bytes, str]:
        """
        Preprocesses an image: resizing, cropping, rotation, contrast, grayscale.
        Returns (processed_bytes, mime_type).
        """
        # Load image
        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input))
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            img = image_input.copy()
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        # Auto-orient based on EXIF tag if present
        img = ImageOps.exif_transpose(img) or img

        # Rotate
        if rotate_deg != 0:
            img = img.rotate(-rotate_deg, expand=True)

        # Crop (left, upper, right, lower)
        if crop_box:
            img = img.crop(crop_box)

        # Resize preserving aspect ratio if exceeding bounds
        if resize_max and (img.width > resize_max[0] or img.height > resize_max[1]):
            img.thumbnail(resize_max, Image.Resampling.LANCZOS)

        # Grayscale
        if grayscale:
            img = img.convert("L")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # Contrast
        if contrast_factor is not None and contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)

        # Brightness
        if brightness_factor is not None and brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)

        # Export to bytes
        fmt = output_format.upper()
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")

        out_buf = io.BytesIO()
        img.save(out_buf, format=fmt, quality=90)
        mime = f"image/{fmt.lower()}"
        return out_buf.getvalue(), mime

    # -------------------------------------------------------------------------
    # Geometric and Shape Detection Heuristics (OpenCV)
    # -------------------------------------------------------------------------
    def detect_shapes_and_geometry(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Uses OpenCV contour analysis and polygon approximation to identify
        geometric shapes (rectangles, triangles, circles, polygons) and bounding boxes.
        """
        if not HAS_OPENCV:
            return {"available": False, "reason": "OpenCV not installed in current environment"}

        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return {"available": False, "error": f"Failed to load image from {image_path}"}

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            shapes = []
            h, w = gray.shape

            for c in contours:
                area = cv2.contourArea(c)
                if area < 80 or area > (w * h * 0.95):
                    continue

                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                x, y, cw, ch = cv2.boundingRect(approx)

                shape_type = "polygon"
                vertices = len(approx)

                if vertices == 3:
                    shape_type = "triangle"
                elif vertices == 4:
                    aspect_ratio = float(cw) / float(ch)
                    if 0.95 <= aspect_ratio <= 1.05:
                        shape_type = "square"
                    else:
                        shape_type = "rectangle"
                elif vertices > 6:
                    # Circularity check
                    circularity = 4 * np.pi * (area / (peri * peri)) if peri > 0 else 0
                    if circularity > 0.7:
                        shape_type = "circle"
                    else:
                        shape_type = "ellipse/polygon"

                shapes.append({
                    "type": shape_type,
                    "vertices": vertices,
                    "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                    "area": float(area)
                })

            return {
                "available": True,
                "image_dimensions": {"width": w, "height": h},
                "detected_shapes_count": len(shapes),
                "shapes": shapes[:50]  # cap to top 50
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # PDF, DOCX, and PPTX Image Extraction
    # -------------------------------------------------------------------------
    def extract_images_from_pdf(self, pdf_path: Union[str, Path], output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Extracts embedded figure and page images from a PDF using pypdf.
        """
        extracted = []
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_path))
            stem = Path(pdf_path).stem

            if output_dir is None:
                output_dir = Path(pdf_path).parent / f"{stem}_images"
            output_dir.mkdir(parents=True, exist_ok=True)

            img_idx = 0
            for page_idx, page in enumerate(reader.pages):
                if hasattr(page, "images"):
                    for img_name, img_obj in page.images.items():
                        img_idx += 1
                        out_name = f"page_{page_idx+1}_img_{img_idx}_{img_name}"
                        out_path = output_dir / out_name
                        with open(out_path, "wb") as f:
                            f.write(img_obj.data)

                        extracted.append({
                            "page": page_idx + 1,
                            "filename": out_name,
                            "path": str(out_path),
                            "size_bytes": len(img_obj.data)
                        })
        except Exception as e:
            logger.warning(f"Error extracting images from PDF: {e}")

        return extracted

    def extract_images_from_docx(self, docx_path: Union[str, Path], output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Extracts embedded figures and graphics from a Word DOCX document.
        """
        import zipfile
        extracted = []
        try:
            stem = Path(docx_path).stem
            if output_dir is None:
                output_dir = Path(docx_path).parent / f"{stem}_docx_images"
            output_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(str(docx_path), "r") as z:
                for file_info in z.infolist():
                    if file_info.filename.startswith("word/media/"):
                        img_bytes = z.read(file_info.filename)
                        base_name = os.path.basename(file_info.filename)
                        out_path = output_dir / base_name
                        with open(out_path, "wb") as f:
                            f.write(img_bytes)

                        extracted.append({
                            "filename": base_name,
                            "path": str(out_path),
                            "size_bytes": len(img_bytes)
                        })
        except Exception as e:
            logger.warning(f"Error extracting images from DOCX: {e}")

        return extracted

    def extract_images_from_pptx(self, pptx_path: Union[str, Path], output_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Extracts embedded pictures and slides from PowerPoint presentations.
        """
        import zipfile
        extracted = []
        try:
            stem = Path(pptx_path).stem
            if output_dir is None:
                output_dir = Path(pptx_path).parent / f"{stem}_pptx_images"
            output_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(str(pptx_path), "r") as z:
                for file_info in z.infolist():
                    if file_info.filename.startswith("ppt/media/"):
                        img_bytes = z.read(file_info.filename)
                        base_name = os.path.basename(file_info.filename)
                        out_path = output_dir / base_name
                        with open(out_path, "wb") as f:
                            f.write(img_bytes)

                        extracted.append({
                            "filename": base_name,
                            "path": str(out_path),
                            "size_bytes": len(img_bytes)
                        })
        except Exception as e:
            logger.warning(f"Error extracting images from PPTX: {e}")

        return extracted

    # -------------------------------------------------------------------------
    # Specialized Prompts for Visual Understanding
    # -------------------------------------------------------------------------
    def get_specialized_prompt(self, mode: str, user_query: Optional[str] = None) -> str:
        base_prompt = ""
        mode = (mode or "general").lower()

        if mode == "ocr":
            base_prompt = (
                "You are an expert OCR and document analysis engine.\n"
                "1. Extract ALL readable text from this image accurately.\n"
                "2. Transcribe text in natural reading order.\n"
                "3. Preserve the approximate spatial relationships, paragraphs, headers, and bullet points.\n"
                "4. If there are signs, labels, legends, or annotations, transcribe them clearly.\n"
                "5. If handwriting or low-resolution text is present, provide your best transcription and mark uncertainties with [?]."
            )
        elif mode in ("chart_graph", "graph", "chart"):
            base_prompt = (
                "You are an expert data visualization and scientific chart analyst.\n"
                "Analyze this graph or chart thoroughly:\n"
                "1. **Graph Type**: Identify the type (line graph, bar chart, scatter plot, histogram, pie chart, etc.).\n"
                "2. **Axes & Scales**: Identify the X-axis and Y-axis labels, units of measurement, scales, and tick marks.\n"
                "3. **Legend & Series**: Identify the data series, colors, categories, or groups represented.\n"
                "4. **Trends & Patterns**: Describe overall trends (increases, decreases, plateaus, seasonality, correlations).\n"
                "5. **Key Data Points**: Identify maximum/highest points, minimum/lowest points, peaks, valleys, outliers, and intersections.\n"
                "6. **Estimated Values**: Where relevant, provide estimated numerical values for plotted data points. Clearly distinguish estimated values (~X) from exact labeled numbers.\n"
                "7. **Interpretation**: Explain what the chart signifies and summarize the primary conclusions."
            )
        elif mode in ("diagram", "flowchart"):
            base_prompt = (
                "You are an expert technical diagram and flowchart analyst.\n"
                "Analyze this diagram or flowchart:\n"
                "1. **Diagram Type**: Identify the type (flowchart, system architecture, UML class/sequence, network topology, electrical, block diagram, etc.).\n"
                "2. **Components & Entities**: List all components, blocks, nodes, states, or entities.\n"
                "3. **Connections & Flow**: Detail how components are connected (arrows, directions, inputs/outputs, communication protocols, decision branches).\n"
                "4. **Sequence of Operations**: Walk through the chronological sequence from start to finish.\n"
                "5. **Decision Points & Conditions**: Detail conditional branches (Yes/No, true/false) and their outcomes.\n"
                "6. **Summary**: Provide a clear overview of what system or process this diagram specifies."
            )
        elif mode == "table":
            base_prompt = (
                "You are an expert tabular data extraction engine.\n"
                "Extract and interpret the table in this image:\n"
                "1. Identify table headers (columns) and row labels.\n"
                "2. Render the extracted table in clean, valid Markdown table format.\n"
                "3. Identify relationships, units, and any notes or footers.\n"
                "4. Note any missing, obscured, or merged cells."
            )
        else:
            base_prompt = (
                "You are an expert multimodal visual intelligence assistant.\n"
                "Analyze this image comprehensively:\n"
                "1. **Scene & Context**: Describe what the image shows in detail.\n"
                "2. **Primary Objects & Elements**: Identify the main objects, people, components, text, or visual artifacts.\n"
                "3. **Visual Relationships**: Describe spatial arrangement, interactions, colors, lighting, and composition.\n"
                "4. **Key Details**: Highlight any notable, unusual, or technical aspects of interest."
            )

        if user_query and user_query.strip():
            base_prompt += f"\n\nSPECIFIC USER QUESTION/REQUEST TO ADDRESS:\n{user_query.strip()}"

        return base_prompt

vision_service = VisionService()
