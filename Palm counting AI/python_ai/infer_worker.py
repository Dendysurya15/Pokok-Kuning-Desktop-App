"""
YOLO inference worker. Reads JSON lines from stdin, runs predict, writes JSON to stdout.
Load model .pt once per model path; Rust sends one request per image.
"""
from __future__ import annotations

import json
import os
import sys

# Redirect stderr to help with debugging
def log_error(msg: str) -> None:
    """Log error to stderr (will be captured by Rust)"""
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)


def preprocess_image(image_path: str) -> tuple[bool, str | None]:
    """
    Validate and optionally convert image to RGB. Returns (ok, path_to_use).
    If conversion needed, writes temp _temp_rgb.jpg and returns that path.
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            mode = img.mode
            if mode in ("RGB", "L"):
                return True, image_path
            img = img.convert("RGB")
            base = os.path.splitext(image_path)[0]
            temp_path = base + "_temp_rgb.jpg"
            img.save(temp_path, "JPEG", quality=95)
            return True, temp_path
    except Exception:
        return False, None


def main() -> None:
    try:
        from ultralytics import YOLO
    except ImportError as e:
        log_error(f"Failed to import ultralytics: {e}")
        log_error("Please install: pip install ultralytics")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected import error: {e}")
        sys.exit(1)

    cached_path: str | None = None
    cached_model: "YOLO | None" = None

    def get_model(path: str) -> "YOLO":
        nonlocal cached_path, cached_model
        path = os.path.abspath(path)
        if path != cached_path:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Model file not found: {path}")
            try:
                cached_model = YOLO(path)
                cached_path = path
            except Exception as e:
                log_error(f"Failed to load model {path}: {e}")
                raise
        assert cached_model is not None
        return cached_model

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            log_error(f"Invalid JSON input: {e}")
            out = {"detections": [], "error": f"Invalid JSON: {e}"}
            print(json.dumps(out), flush=True)
            continue

        image_path = req.get("image")
        model_path = req.get("model")
        imgsz = int(req.get("imgsz", 1280))
        conf = float(req.get("conf", 0.2))
        iou = float(req.get("iou", 0.2))
        dev = (req.get("device") or "auto").lower()
        if dev == "auto":
            try:
                import torch

                dev = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                dev = "cpu"
        max_det = int(req.get("max_det", 10000))

        if not image_path or not os.path.isfile(image_path):
            err_msg = f"Missing or invalid image path: {image_path}"
            log_error(err_msg)
            print(json.dumps({"detections": [], "error": err_msg}), flush=True)
            continue
        if not model_path or not os.path.isfile(model_path):
            err_msg = f"Missing or invalid model path: {model_path}"
            log_error(err_msg)
            print(json.dumps({"detections": [], "error": err_msg}), flush=True)
            continue

        temp_path: str | None = None
        try:
            ok, use_path = preprocess_image(image_path)
            if not ok:
                print(json.dumps({"detections": [], "error": "Invalid or unsupported image"}), flush=True)
                continue
            if use_path != image_path:
                temp_path = use_path

            model = get_model(model_path)
            run_device = "cuda" if dev == "cuda" else "cpu"
            try:
                results = model.predict(
                    source=use_path,
                    imgsz=imgsz,
                    conf=conf,
                    iou=iou,
                    max_det=max_det,
                    device=run_device,
                    verbose=False,
                    save=False,
                )
            except Exception as pred_err:
                if run_device == "cuda":
                    results = model.predict(
                        source=use_path,
                        imgsz=imgsz,
                        conf=conf,
                        iou=iou,
                        max_det=max_det,
                        device="cpu",
                        verbose=False,
                        save=False,
                    )
                else:
                    raise pred_err

            detections = []
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    xyxy = box.xyxy[0].cpu().tolist()
                    x1, y1, x2, y2 = xyxy
                    detections.append({
                        "x1": round(x1, 4),
                        "y1": round(y1, 4),
                        "x2": round(x2, 4),
                        "y2": round(y2, 4),
                        "class_id": int(box.cls.item()),
                        "conf": round(float(box.conf.item()), 4),
                    })

            print(json.dumps({"detections": detections, "error": None}), flush=True)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            log_error(f"Exception during inference: {e}\n{error_trace}")
            print(json.dumps({"detections": [], "error": str(e)}), flush=True)
        finally:
            if temp_path and os.path.isfile(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
