# ============================================================
# Local Document Analyzer
# ============================================================

import io
import os
import cv2
import torch
import numpy as np
import json
import gc
from PIL import Image, ImageChops
from pathlib import Path
from difflib import SequenceMatcher
from skimage.filters import threshold_otsu
from torchvision import models, transforms
from pdf2image import convert_from_path
import pytesseract
import shutil
import matplotlib.pyplot as plt
from datetime import datetime
from local_storage import LocalStorage


# ------------------------------------------------------------
# 1️⃣ Define the Core Analyzer Logic (As a Class)
# ------------------------------------------------------------

class DocumentAnalyzerCore:
    """Performs image and PDF forensic analysis using ELA, OCR, and CNN."""

    def __init__(self, loan_id=None, storage=None):
        # ✅ Auto-detect or set fallback Tesseract path for Windows
        tesseract_path = shutil.which("tesseract")
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Using system Tesseract at: {tesseract_path}")
        else:
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            print("⚠️ Using fallback Tesseract path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

        # Optional: Print version check for debugging
        try:
            version = pytesseract.get_tesseract_version()
            print(f"🧠 Tesseract version detected: {version}")
        except Exception as e:
            print(f"⚠️ Could not retrieve Tesseract version: {e}")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._load_model()
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])
        
        # Local artifact storage configuration
        self.loan_id = loan_id
        self.storage = storage or LocalStorage()
        print(f"Local artifact storage initialized at: {self.storage.root}")

    def _load_model(self):
        # Using ResNet50 for GradCAM compatibility (same as sample da.py)
        model = models.resnet50(weights=None)
        model = model.to(self.device)
        model.eval()
        return model

    def normalize(self, v, mx=1.0):
        return max(0.0, min(1.0, v / mx))

    def ocr_text_similarity(self, pdf_text, pil_img):
        print("Comparing OCR output vs provided text...")
        """Compare OCR output vs provided text."""
        try:
            ocr = pytesseract.image_to_string(pil_img, lang='eng') or ""
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            return 0.0
        a = " ".join(pdf_text.split()).lower()
        b = " ".join(ocr.split()).lower()
        if not a and not b:
            return 1.0
        if not a and b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def compute_ela(self, pil_img, quality=90):
        """Compute Error Level Analysis image (PIL) - from sample da.py."""
        print("Computing ELA...")
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")
        ela_img = ImageChops.difference(pil_img.convert("RGB"), recompressed)
        extrema = ela_img.getextrema()
        max_diff = max([e[1] for e in extrema]) or 1
        scale = 255.0 / max_diff
        ela_np = np.array(ela_img).astype("float32") * scale
        ela_np = np.clip(ela_np, 0, 255).astype("uint8")
        return Image.fromarray(ela_np)
    
    def compute_noise_residual(self, pil_img):
        """High-pass filter / Laplacian to get noise residual (PIL) - from sample da.py."""
        print("Computing noise residual...")
        gray = np.array(pil_img.convert("L"))
        lap = cv2.Laplacian(gray, ddepth=cv2.CV_32F, ksize=3)
        nm = np.abs(lap)
        nm = nm / (nm.max() + 1e-8) * 255.0
        nm = nm.astype("uint8")
        return Image.fromarray(nm)

    def ela_score(self, pil_img):
        print("Computing ELA-based forgery likelihood score...")
        """Compute ELA-based forgery likelihood score."""
        ela = self.compute_ela(pil_img)
        ela_gray = np.array(ela.convert('L'))
        try:
            thresh = threshold_otsu(ela_gray)
        except Exception:
            thresh = 60
        bw = (ela_gray > max(thresh, 60)).astype('uint8') * 255
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = ela_gray.shape[:2]
        page_area = h * w
        large_area = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > (page_area * 0.001))
        area_ratio = large_area / page_area
        mean_intensity = float(ela_gray.mean()) / 255.0
        score = self.normalize(area_ratio, 0.05) * 0.8 + self.normalize(mean_intensity, 0.25) * 0.2
        return score

    def generate_gradcam(self, pil_img, target_class=None):
        """Generate Grad-CAM using last conv layer of ResNet50 and return as bytes."""
        print(f"Generating GradCAM heatmap...")
        self.model.eval()
        img_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        features = None
        grads = None

        def forward_hook(module, input, output):
            nonlocal features
            features = output

        def backward_hook(module, grad_in, grad_out):
            nonlocal grads
            grads = grad_out[0]

        # register hooks on layer4[-1].conv3
        last_conv = self.model.layer4[-1].conv3
        h_f = last_conv.register_forward_hook(forward_hook)
        h_b = last_conv.register_backward_hook(backward_hook)

        logits = self.model(img_tensor)
        if target_class is None:
            target_class = int(logits.argmax(dim=1)[0].item())

        score = logits[0, target_class]
        self.model.zero_grad()
        score.backward(retain_graph=False)

        # detach
        gradients = grads.detach()
        activations = features.detach()

        # global average pooling on gradients
        weights = gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam.squeeze().cpu().numpy()
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)

        # resize to original image size
        cam_resized = cv2.resize(cam, (pil_img.width, pil_img.height))
        heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(np.array(pil_img.convert("RGB")), 0.6, heatmap, 0.4, 0)

        # Convert to bytes instead of saving
        buf = io.BytesIO()
        plt.imsave(buf, overlay, format='png')
        buf.seek(0)
        image_bytes = buf.read()
        
        h_f.remove()
        h_b.remove()
        print(f"✅ GradCAM generated in memory")
        return image_bytes
    
    def save_file(self, local_file_path, storage_key):
        """Copy a generated artifact into local application storage."""
        try:
            data = Path(local_file_path).read_bytes()
            path = self.storage.write_bytes(*storage_key.split("/"), data=data)
            return str(path)
        except OSError as exc:
            print(f"Local artifact save failed: {exc}")
            return None

    def save_bytes(self, file_bytes, storage_key, content_type="image/png"):
        """Save generated bytes directly to local application storage."""
        del content_type
        try:
            path = self.storage.write_bytes(*storage_key.split("/"), data=file_bytes)
            print(f"Saved local artifact: {path}")
            return str(path)
        except OSError as exc:
            print(f"Local artifact save failed: {exc}")
            return None

    def score_image(self, pil_img):
        """Ensemble scoring from sample da.py - returns (ensemble_score, details_dict)."""
        print("Scoring image with ensemble method...")
        # ELA and noise
        try:
            ela_img = self.compute_ela(pil_img)
        except Exception:
            buf = io.BytesIO()
            pil_img.convert("RGB").save(buf, format="JPEG", quality=90)
            buf.seek(0)
            recompressed = Image.open(buf).convert("RGB")
            ela_img = ImageChops.difference(pil_img.convert("RGB"), recompressed)

        noise_img = self.compute_noise_residual(pil_img)

        # Model probs: original image
        with torch.no_grad():
            t = self.transform(pil_img).unsqueeze(0).to(self.device)
            logits = self.model(t)
            probs = torch.nn.functional.softmax(logits, dim=1)[0].cpu().numpy()
            model_prob_orig = float(probs.max())

        # Model probs: ELA image
        ela_rgb = ela_img.convert("RGB")
        with torch.no_grad():
            t2 = self.transform(ela_rgb).unsqueeze(0).to(self.device)
            logits2 = self.model(t2)
            probs2 = torch.nn.functional.softmax(logits2, dim=1)[0].cpu().numpy()
            model_prob_ela = float(probs2.max())

        # Heuristic statistics from ELA/noise
        ela_np = np.array(ela_img.convert("L")).astype("float32") / 255.0
        ela_mean = float(ela_np.mean())
        ela_std = float(ela_np.std())

        noise_np = np.array(noise_img).astype("float32") / 255.0
        noise_mean = float(noise_np.mean())
        noise_std = float(noise_np.std())

        # Ensemble score calculation
        ensemble_score = (
            0.45 * model_prob_orig +
            0.35 * model_prob_ela +
            0.1 * min(1.0, ela_std * 5) +
            0.1 * min(1.0, noise_std * 5)
        )

        details = {
            "model_prob_orig": round(model_prob_orig, 4),
            "model_prob_ela": round(model_prob_ela, 4),
            "ela_mean": round(ela_mean, 4),
            "ela_std": round(ela_std, 4),
            "noise_mean": round(noise_mean, 4),
            "noise_std": round(noise_std, 4)
        }
        return ensemble_score, details

    def analyze_document(self, path, dpi=200, tamper_threshold=0.5, verbose=False):
        """Analyze a single document and save GradCAM artifacts locally."""
        print(f"\n{'='*60}")
        print(f"Analyzing document: {os.path.basename(path)}")
        print(f"{'='*60}")
        
        ext = os.path.splitext(path)[1].lower()
        fname = os.path.basename(path)
        
        if ext == '.pdf':
            try:
                pages = convert_from_path(path, dpi=dpi)
                print(f"✅ PDF converted: {len(pages)} page(s)")
            except Exception as e:
                return [{"error": f"Failed to convert PDF: {e}"}]
        else:
            try:
                pages = [Image.open(path).convert("RGB")]
                print(f"✅ Image loaded successfully")
            except Exception as e:
                return [{"error": f"Failed to open image: {e}"}]

        results = []
        for idx, page_img in enumerate(pages, start=1):
            print(f"\n--- Processing Page {idx} ---")
            
            # Use ensemble scoring from sample da.py
            ensemble_score, details = self.score_image(page_img)
            
            # Determine tampering level
            # High: score > 0.6
            # Medium: score >= 0.55 and <= 0.6
            # Low: score < 0.55
            if ensemble_score > 0.6:
                level = "High"
            elif ensemble_score >= 0.55:
                level = "Medium"
            else:
                level = "Low"
            
            page_entry = {
                "page": idx,
                "ensemble_score": round(float(ensemble_score), 4),
                "tampering_level": level,
                "details": details,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # Generate GradCAM if tampering detected
            if ensemble_score >= tamper_threshold or ensemble_score >= 0.55:
                print(f"⚠️ Tampering detected (score: {ensemble_score:.4f})! Generating GradCAM...")
                
                gradcam_filename = f"{os.path.splitext(fname)[0]}_page{idx}_gradcam.png"
                
                try:
                    # Generate GradCAM in memory (no local save)
                    gradcam_bytes = self.generate_gradcam(page_img)
                    
                    if self.loan_id:
                        storage_key = f"{self.loan_id}/gradcam/{gradcam_filename}"
                        local_path = self.save_bytes(gradcam_bytes, storage_key)
                        if local_path:
                            page_entry["gradcam_url"] = f"/gradcam/{self.loan_id}/{gradcam_filename}"
                            page_entry["gradcam_path"] = local_path
                    else:
                        print("Loan ID not provided. GradCAM was not saved.")
                        
                except Exception as e:
                    page_entry["gradcam_error"] = str(e)
                    print(f"❌ GradCAM generation failed: {e}")
            else:
                print(f"✅ No tampering detected (score: {ensemble_score:.4f})")

            results.append(page_entry)
            gc.collect()

        return results

    def analyze_folder(self, folder_path, dpi=200, tamper_threshold=0.5, verbose=False):
        """Analyze all supported documents in a folder."""
        files = [f for f in os.listdir(folder_path)
                 if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))]

        if not files:
            return {"status": "⚠️ No documents found."}

        all_results = {}
        for f in files:
            path = os.path.join(folder_path, f)
            all_results[f] = self.analyze_document(path, dpi=dpi, tamper_threshold=tamper_threshold, verbose=verbose)
        return all_results


# ------------------------------------------------------------
# Public document-analysis helper
# ------------------------------------------------------------

def analyze_documents(path: str, loan_id: str = None, tamper_threshold: float = 0.5) -> str:
    """
    Analyzes documents for tampering using ensemble forensic methods (ELA, noise residual, CNN).
    Generates GradCAM heatmaps for suspicious documents and saves them locally.
    
    Args:
        path: File or folder path to analyze
        loan_id: Loan ID for local storage path (format: LID********)
        tamper_threshold: Threshold for tampering detection (default: 0.5)
    
    Returns:
        JSON string with analysis results including local GradCAM URLs if tampering is detected
    """
    analyzer = DocumentAnalyzerCore(loan_id=loan_id)
    
    # If path doesn't exist, try searching in Documents folder
    if not os.path.exists(path):
        if not os.path.dirname(path):
            documents_path = os.path.join("Documents", path)
            if os.path.exists(documents_path):
                path = documents_path
                print(f"✅ Found file in Documents folder: {path}")
            else:
                error_result = {
                    "status": "error",
                    "message": f"File not found - {path} (also checked Documents/{path})"
                }
                return json.dumps(error_result, indent=2)
        else:
            error_result = {
                "status": "error",
                "message": f"File not found - {path}"
            }
            return json.dumps(error_result, indent=2)
    
    # Analyze documents
    if os.path.isdir(path):
        results = analyzer.analyze_folder(path, tamper_threshold=tamper_threshold, verbose=True)
        output = {
            "status": "success",
            "analysis_type": "folder",
            "path": path,
            "loan_id": loan_id,
            "tamper_threshold": tamper_threshold,
            "results": results
        }
    else:
        results = analyzer.analyze_document(path, tamper_threshold=tamper_threshold, verbose=True)
        output = {
            "status": "success",
            "analysis_type": "single_file",
            "path": path,
            "loan_id": loan_id,
            "tamper_threshold": tamper_threshold,
            "file_name": os.path.basename(path),
            "results": results
        }
    
    return json.dumps(output, indent=2)
