import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.agent.permissions import permission_manager
from app.services.vision_service import vision_service
from app.services.llm_service import llm_service

def analyze_image(
    image_path: str,
    mode: str = "general",
    query: Optional[str] = None,
    grayscale: bool = False,
    contrast: Optional[float] = None,
    rotate: int = 0,
    crop: Optional[list] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    General image understanding, OCR, flowchart/diagram analysis, and graph/chart inspection
    using multimodal vision models combined with computer vision preprocessing (Pillow/OpenCV).

    Modes:
    - 'ocr': Extract all readable text, labels, and annotations.
    - 'chart_graph': Analyze graphs, plots, charts (axes, trends, peaks, numerical estimates).
    - 'diagram': Understand flowcharts, block diagrams, component connections, sequence of operations.
    - 'table': Extract structured tabular data into Markdown.
    - 'general': Scene understanding, object recognition, visual elements.
    - 'geometry': Contour and geometric shape detection via OpenCV.
    """
    mode = (mode or "general").lower().strip()
    try:
        # Check if path is in uploads or workspace
        workspace = permission_manager.get_workspace_dir()
        resolved_path = None

        candidate = Path(image_path)
        if candidate.is_absolute() and candidate.exists():
            resolved_path = candidate
        else:
            # 1. Try relative to workspace
            try:
                p1 = permission_manager.resolve_safe_path(image_path)
                if p1.exists():
                    resolved_path = p1
            except Exception:
                pass

            # 2. Try in data/uploads
            if not resolved_path:
                upload_p = workspace / "data" / "uploads" / image_path
                if upload_p.exists():
                    resolved_path = upload_p

        if not resolved_path or not resolved_path.exists():
            return {
                "success": False,
                "error": f"Image file '{image_path}' not found in workspace or uploads directory."
            }

        # Check if the file is a document containing embedded images (PDF/DOCX/PPTX)
        ext = resolved_path.suffix.lower()
        if ext == ".pdf":
            extracted = vision_service.extract_images_from_pdf(resolved_path)
            if not extracted:
                return {
                    "success": False,
                    "error": f"No embedded images or figures found inside PDF '{image_path}'"
                }
            # Pick first image or analyzed image
            resolved_path = Path(extracted[0]["path"])
        elif ext == ".docx":
            extracted = vision_service.extract_images_from_docx(resolved_path)
            if not extracted:
                return {
                    "success": False,
                    "error": f"No embedded images found inside DOCX '{image_path}'"
                }
            resolved_path = Path(extracted[0]["path"])
        elif ext == ".pptx":
            extracted = vision_service.extract_images_from_pptx(resolved_path)
            if not extracted:
                return {
                    "success": False,
                    "error": f"No embedded images found inside PPTX '{image_path}'"
                }
            resolved_path = Path(extracted[0]["path"])

        # Complementary geometric detection via OpenCV if requested or as auxiliary data
        cv_shapes = None
        if mode == "geometry":
            geom_result = vision_service.detect_shapes_and_geometry(resolved_path)
            return {
                "success": True,
                "mode": "geometry",
                "image_path": str(resolved_path),
                "geometric_analysis": geom_result
            }

        # Preprocessing image (resize, contrast, grayscale, rotate, crop)
        crop_tuple = tuple(crop) if crop and len(crop) == 4 else None
        img_bytes, mime = vision_service.preprocess_image(
            resolved_path,
            grayscale=grayscale,
            contrast_factor=contrast,
            rotate_deg=rotate,
            crop_box=crop_tuple
        )

        # Build prompt
        prompt = vision_service.get_specialized_prompt(mode=mode, user_query=query)

        # Call multimodal vision model
        vision_res = llm_service.analyze_image_with_model(
            image_bytes=img_bytes,
            mime_type=mime,
            prompt=prompt,
            provider=provider,
            model=model
        )

        # Optionally enrich with OpenCV contour info if diagram or chart
        if mode in ("chart_graph", "diagram"):
            cv_shapes = vision_service.detect_shapes_and_geometry(resolved_path)

        return {
            "success": vision_res.get("success", False),
            "mode": mode,
            "image_path": str(resolved_path),
            "analysis": vision_res.get("analysis", ""),
            "model_used": f"{vision_res.get('provider')}:{vision_res.get('model')}",
            "cv_geometry": cv_shapes if cv_shapes and cv_shapes.get("available") else None,
            "error": vision_res.get("error")
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
