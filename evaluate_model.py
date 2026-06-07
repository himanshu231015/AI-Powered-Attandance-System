# -*- coding: utf-8 -*-
"""
============================================================
  AI-Powered Attendance System - Model Evaluation Script
============================================================
Covers three evaluation axes:
  1. Classification  -> Accuracy, Precision, Recall, F1, Confusion Matrix
  2. Verification    -> ROC Curve, AUC, EER, FAR / FRR
  3. Embedding       -> RMSE, Cosine Similarity, Euclidean Distance

Run from the project root:
    python evaluate_model.py

Requirements (already in requirements.txt):
    face_recognition, scikit-learn, numpy, opencv-python
    + matplotlib (pip install matplotlib) for plots
"""

import sys
import io
# Force UTF-8 on Windows console to avoid cp1252 errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import pickle
import warnings
import numpy as np
from pathlib import Path
from itertools import combinations

warnings.filterwarnings("ignore")

# -- Try importing heavy deps -------------------------------------------------
try:
    import face_recognition
except ImportError:
    sys.exit("ERROR: 'face_recognition' not installed. Run: pip install face_recognition")

try:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, roc_curve, auc, ConfusionMatrixDisplay
    )
    from sklearn.model_selection import StratifiedKFold
    from sklearn.neighbors import KNeighborsClassifier
except ImportError:
    sys.exit("ERROR: 'scikit-learn' not installed. Run: pip install scikit-learn")

try:
    import matplotlib
    matplotlib.use("Agg")   # non-interactive backend -> saves PNG files
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("WARNING: matplotlib not found -- skipping plot generation.")
    print("         Install with: pip install matplotlib\n")

# -- Paths --------------------------------------------------------------------
ROOT         = Path(__file__).parent
DATASET_ROOT = ROOT / "database" / "dataset"
MODEL_PATH   = ROOT / "database" / "model.pkl"
CACHE_PATH   = ROOT / "ai_attendance" / "encodings_cache.pkl"
OUTPUT_DIR   = ROOT / "evaluation_output"
OUTPUT_DIR.mkdir(exist_ok=True)

RECOGNITION_THRESHOLD = 0.53   # same as utils.py

SEP = "=" * 60


# =============================================================================
#  STEP 1  Load / Build face encodings from dataset
# =============================================================================

def load_dataset():
    """
    Walk DATASET_ROOT recursively.
    Folder pattern: <roll_number>_<Name>  e.g. 0873Al231001_Aastha Malviya
    Returns:
        encodings : np.ndarray  shape (N, 128)
        labels    : np.ndarray  roll-number strings (ground truth)
        names     : dict  {roll_number: full_name}
    """
    print("\n" + SEP)
    print("  STEP 1 -- Loading dataset from:", DATASET_ROOT)
    print(SEP)

    # Try to load encoding cache
    cache = {}
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "rb") as f:
                cache = pickle.load(f)
            print(f"  [OK] Loaded {len(cache)} cached encodings")
        except Exception as e:
            print(f"  [!] Cache load error: {e}")

    encodings, labels, names = [], [], {}

    for person_dir in sorted(DATASET_ROOT.rglob("*")):
        if not person_dir.is_dir():
            continue
        folder_name = person_dir.name
        if "_" not in folder_name:
            continue

        roll_number = folder_name.split("_")[0]
        # Basic validation -- roll starts with digits/alnum
        if not roll_number.replace("Al", "").isalnum():
            continue

        # Only process directories with images
        image_files = [
            f for f in person_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png")
        ]
        if not image_files:
            continue

        full_name = " ".join(folder_name.split("_")[1:])
        names[roll_number] = full_name
        print(f"  >> {roll_number}: {full_name} -- {len(image_files)} image(s)")

        for img_path in image_files:
            rel_key = str(img_path.relative_to(DATASET_ROOT))

            if rel_key in cache:
                enc = cache[rel_key]
                if enc is not None:
                    encodings.append(enc)
                    labels.append(roll_number)
            else:
                try:
                    img  = face_recognition.load_image_file(str(img_path))
                    encs = face_recognition.face_encodings(img)
                    if encs:
                        encodings.append(encs[0])
                        labels.append(roll_number)
                        cache[rel_key] = encs[0]
                    else:
                        cache[rel_key] = None
                        print(f"    [!] No face detected in {img_path.name}")
                except Exception as ex:
                    print(f"    [!] Error on {img_path.name}: {ex}")

    print(f"\n  Total encodings  : {len(encodings)}")
    print(f"  Unique identities: {len(set(labels))}")
    return np.array(encodings), np.array(labels), names


# =============================================================================
#  STEP 2  Classification Metrics  (cross-validated KNN)
# =============================================================================

def evaluate_classification(encodings, labels, names):
    print("\n" + SEP)
    print("  STEP 2 -- Classification Metrics")
    print(SEP)

    unique_classes = np.unique(labels)
    n_classes = len(unique_classes)

    if n_classes < 2:
        print("  [!] Need >= 2 identities. Skipping.")
        return None

    # StratifiedKFold -- min(5, n_samples) folds
    n_splits = min(5, len(encodings))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    all_true, all_pred = [], []

    for fold, (train_idx, test_idx) in enumerate(skf.split(encodings, labels), 1):
        X_train, X_test = encodings[train_idx], encodings[test_idx]
        y_train, y_test = labels[train_idx],   labels[test_idx]

        knn = KNeighborsClassifier(n_neighbors=1, algorithm="ball_tree", weights="distance")
        knn.fit(X_train, y_train)

        distances, _ = knn.kneighbors(X_test, n_neighbors=1)
        y_pred_raw   = knn.predict(X_test)

        # Apply distance threshold -> UNKNOWN if too far
        y_pred = np.where(distances[:, 0] <= RECOGNITION_THRESHOLD, y_pred_raw, "UNKNOWN")

        all_true.extend(y_test)
        all_pred.extend(y_pred)

    all_true = np.array(all_true)
    all_pred = np.array(all_pred)

    acc  = accuracy_score(all_true, all_pred)
    prec = precision_score(all_true, all_pred, labels=list(unique_classes),
                           average="weighted", zero_division=0)
    rec  = recall_score(all_true, all_pred, labels=list(unique_classes),
                        average="weighted", zero_division=0)
    f1   = f1_score(all_true, all_pred, labels=list(unique_classes),
                    average="weighted", zero_division=0)
    unknown_rate = np.mean(all_pred == "UNKNOWN") * 100

    print(f"\n  Aggregate Results (threshold = {RECOGNITION_THRESHOLD})")
    print(f"  {'Accuracy':<22}: {acc*100:6.2f}%")
    print(f"  {'Precision (weighted)':<22}: {prec*100:6.2f}%")
    print(f"  {'Recall    (weighted)':<22}: {rec*100:6.2f}%")
    print(f"  {'F1 Score  (weighted)':<22}: {f1*100:6.2f}%")
    print(f"  {'Unknown Rate':<22}: {unknown_rate:6.2f}%")

    # Per-identity report
    print("\n  Per-Identity Results:")
    print(f"  {'Roll Number':<26} {'Name':<28} {'Prec':>6} {'Rec':>6} {'F1':>6} {'N':>5}")
    print("  " + "-" * 80)
    for roll in sorted(unique_classes):
        mask_t = all_true == roll
        mask_p = all_pred == roll
        tp = int(np.sum(mask_t & mask_p))
        fp = int(np.sum(~mask_t & mask_p))
        fn = int(np.sum(mask_t & ~mask_p))
        p  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f  = 2*p*r / (p+r) if (p+r) > 0 else 0.0
        n  = int(np.sum(mask_t))
        nm = names.get(roll, "")
        print(f"  {roll:<26} {nm:<28} {p*100:6.1f} {r*100:6.1f} {f*100:6.1f} {n:>5}")

    # Confusion Matrix
    mask_k = (all_true != "UNKNOWN") & (all_pred != "UNKNOWN")
    cm = confusion_matrix(all_true[mask_k], all_pred[mask_k], labels=list(unique_classes))
    print("\n  Confusion Matrix (raw counts):")
    header = "  " + " ".join(f"{r[-4:]:>6}" for r in unique_classes)
    print(header)
    for i, row_label in enumerate(unique_classes):
        row = " ".join(f"{v:>6}" for v in cm[i])
        print(f"  {row_label[-4:]:>6} | {row}")

    if HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(max(6, n_classes + 1), max(5, n_classes + 1)))
        short = [r[-4:] for r in unique_classes]
        disp  = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=short)
        disp.plot(ax=ax, colorbar=True, cmap="Blues")
        ax.set_title("Confusion Matrix -- Face Recognition (KNN, k=1)", fontsize=13, pad=10)
        ax.set_xlabel("Predicted (last 4 digits of roll)")
        ax.set_ylabel("True (last 4 digits of roll)")
        plt.tight_layout()
        path = OUTPUT_DIR / "confusion_matrix.png"
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"\n  [OK] Saved: {path}")

    return {
        "accuracy": acc, "precision": prec,
        "recall": rec,   "f1": f1,
        "unknown_rate": unknown_rate / 100,
        "confusion_matrix": cm,
    }


# =============================================================================
#  STEP 3  Verification Metrics  (ROC, AUC, EER, FAR / FRR)
# =============================================================================

def evaluate_verification(encodings, labels):
    """
    For every pair (i, j):
      score = 1 - euclidean_distance   (higher -> more similar)
      label = 1 if same person, 0 if different
    """
    print("\n" + SEP)
    print("  STEP 3 -- Verification Metrics  (ROC / AUC / EER / FAR / FRR)")
    print(SEP)

    if len(encodings) < 4:
        print("  [!] Need >= 4 encodings. Skipping.")
        return None

    genuine_sc, impostor_sc = [], []
    pair_labels, pair_scores = [], []

    for i, j in combinations(range(len(encodings)), 2):
        dist  = float(np.linalg.norm(encodings[i] - encodings[j]))
        score = 1.0 - dist
        is_g  = int(labels[i] == labels[j])
        pair_labels.append(is_g)
        pair_scores.append(score)
        (genuine_sc if is_g else impostor_sc).append(score)

    pair_labels = np.array(pair_labels)
    pair_scores = np.array(pair_scores)

    print(f"\n  Pair statistics:")
    print(f"  Genuine pairs    : {len(genuine_sc)}")
    print(f"  Impostor pairs   : {len(impostor_sc)}")
    if genuine_sc:
        print(f"  Genuine  score   : mean={np.mean(genuine_sc):.4f}, std={np.std(genuine_sc):.4f}")
    if impostor_sc:
        print(f"  Impostor score   : mean={np.mean(impostor_sc):.4f}, std={np.std(impostor_sc):.4f}")

    # ROC / AUC
    fpr, tpr, thr_roc = roc_curve(pair_labels, pair_scores)
    roc_auc = auc(fpr, tpr)
    print(f"\n  AUC (ROC)        : {roc_auc:.4f}")

    # FAR / FRR at system threshold
    verify_thr = 1.0 - RECOGNITION_THRESHOLD   # score threshold
    predicted  = (pair_scores >= verify_thr).astype(int)
    gen_mask   = pair_labels == 1
    imp_mask   = pair_labels == 0

    far = float(np.mean(predicted[imp_mask] == 1)) if imp_mask.any() else 0.0
    frr = float(np.mean(predicted[gen_mask] == 0)) if gen_mask.any() else 0.0

    print(f"  Threshold        : {RECOGNITION_THRESHOLD} (dist) / {verify_thr:.3f} (score)")
    print(f"  FAR (False Accept Rate): {far*100:.2f}%")
    print(f"  FRR (False Reject Rate): {frr*100:.2f}%")

    # EER -- where FPR meets FNR
    fnr      = 1.0 - tpr
    eer_idx  = int(np.argmin(np.abs(fpr - fnr)))
    eer      = float((fpr[eer_idx] + fnr[eer_idx]) / 2)
    eer_thr  = float(thr_roc[eer_idx])
    print(f"  EER              : {eer*100:.2f}%  (at score threshold {eer_thr:.4f})")

    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # ROC Curve
        axes[0].plot(fpr, tpr, color="#4f86f7", lw=2,
                     label=f"ROC (AUC = {roc_auc:.4f})")
        axes[0].scatter([fpr[eer_idx]], [tpr[eer_idx]], color="red",
                        zorder=5, s=80, label=f"EER = {eer*100:.1f}%")
        axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
        axes[0].set_xlabel("False Positive Rate (FAR)")
        axes[0].set_ylabel("True Positive Rate (1 - FRR)")
        axes[0].set_title("ROC Curve -- Verification Task")
        axes[0].legend(loc="lower right")
        axes[0].grid(alpha=0.3)

        # FAR / FRR vs threshold
        thr_range = np.linspace(float(pair_scores.min()), float(pair_scores.max()), 300)
        far_v, frr_v = [], []
        for t in thr_range:
            p2 = (pair_scores >= t).astype(int)
            far_v.append(float(np.mean(p2[imp_mask] == 1)) if imp_mask.any() else 0.0)
            frr_v.append(float(np.mean(p2[gen_mask] == 0)) if gen_mask.any() else 0.0)

        axes[1].plot(thr_range, [v*100 for v in far_v], color="#e74c3c", lw=2, label="FAR (%)")
        axes[1].plot(thr_range, [v*100 for v in frr_v], color="#2ecc71", lw=2, label="FRR (%)")
        axes[1].axvline(verify_thr, color="orange", linestyle="--",
                        label=f"System thr ({verify_thr:.2f})")
        axes[1].axvline(eer_thr, color="purple", linestyle=":",
                        label=f"EER thr ({eer_thr:.2f})")
        axes[1].set_xlabel("Score Threshold  (1 - Euclidean Dist)")
        axes[1].set_ylabel("Error Rate (%)")
        axes[1].set_title("FAR / FRR vs Threshold")
        axes[1].legend()
        axes[1].grid(alpha=0.3)

        plt.tight_layout()
        path = OUTPUT_DIR / "roc_far_frr.png"
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"  [OK] Saved: {path}")

    return {"auc": roc_auc, "eer": eer, "far": far, "frr": frr,
            "fpr": fpr, "tpr": tpr}


# =============================================================================
#  STEP 4  Embedding Similarity Metrics
# =============================================================================

def evaluate_embeddings(encodings, labels):
    """
    Pairwise embedding analysis:
      Cosine Similarity, Euclidean Distance, RMSE
    """
    print("\n" + SEP)
    print("  STEP 4 -- Embedding Similarity Metrics")
    print(SEP)

    if len(encodings) < 4:
        print("  [!] Need >= 4 encodings. Skipping.")
        return None

    def cos_sim(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

    gen_cos, imp_cos = [], []
    gen_euc, imp_euc = [], []

    for i, j in combinations(range(len(encodings)), 2):
        cs  = cos_sim(encodings[i], encodings[j])
        euc = float(np.linalg.norm(encodings[i] - encodings[j]))
        if labels[i] == labels[j]:
            gen_cos.append(cs);  gen_euc.append(euc)
        else:
            imp_cos.append(cs);  imp_euc.append(euc)

    gen_cos  = np.array(gen_cos);  imp_cos = np.array(imp_cos)
    gen_euc  = np.array(gen_euc);  imp_euc = np.array(imp_euc)

    # RMSE: genuine pairs vs ideal dist=0, impostor vs ideal dist=1
    rmse_gen = float(np.sqrt(np.mean(gen_euc ** 2)))         if gen_euc.size  else 0.0
    rmse_imp = float(np.sqrt(np.mean((1.0 - imp_euc) ** 2))) if imp_euc.size  else 0.0

    print("\n  --- Cosine Similarity ---")
    if gen_cos.size:
        print(f"  Genuine  pairs mean : {np.mean(gen_cos):.4f}  (ideal -> 1.00)")
    if imp_cos.size:
        print(f"  Impostor pairs mean : {np.mean(imp_cos):.4f}  (ideal -> 0.00 or lower)")
    if gen_cos.size and imp_cos.size:
        print(f"  Separation          : {np.mean(gen_cos) - np.mean(imp_cos):.4f}")

    print("\n  --- Euclidean Distance ---")
    if gen_euc.size:
        print(f"  Genuine  pairs mean : {np.mean(gen_euc):.4f}  (ideal -> 0.00)")
    if imp_euc.size:
        print(f"  Impostor pairs mean : {np.mean(imp_euc):.4f}  (ideal -> > {RECOGNITION_THRESHOLD})")
    if gen_euc.size and imp_euc.size:
        print(f"  Separation          : {np.mean(imp_euc) - np.mean(gen_euc):.4f}")

    print("\n  --- RMSE ---")
    print(f"  RMSE genuine  (vs ideal 0) : {rmse_gen:.4f}")
    print(f"  RMSE impostor (vs ideal 1) : {rmse_imp:.4f}")

    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        bins = np.linspace(0, 1.4, 50)
        if gen_euc.size:
            axes[0].hist(gen_euc,  bins=bins, alpha=0.7, color="#2ecc71", label="Genuine Pairs")
        if imp_euc.size:
            axes[0].hist(imp_euc, bins=bins, alpha=0.7, color="#e74c3c", label="Impostor Pairs")
        axes[0].axvline(RECOGNITION_THRESHOLD, color="orange", linestyle="--", lw=2,
                        label=f"Threshold ({RECOGNITION_THRESHOLD})")
        axes[0].set_xlabel("Euclidean Distance")
        axes[0].set_ylabel("Count")
        axes[0].set_title("Euclidean Distance Distribution")
        axes[0].legend(); axes[0].grid(alpha=0.3)

        bins_c = np.linspace(-0.2, 1.05, 50)
        if gen_cos.size:
            axes[1].hist(gen_cos,  bins=bins_c, alpha=0.7, color="#2ecc71", label="Genuine Pairs")
        if imp_cos.size:
            axes[1].hist(imp_cos, bins=bins_c, alpha=0.7, color="#e74c3c", label="Impostor Pairs")
        cos_thr = 1.0 - RECOGNITION_THRESHOLD
        axes[1].axvline(cos_thr, color="orange", linestyle="--", lw=2,
                        label=f"Equiv. Cosine Thr ({cos_thr:.2f})")
        axes[1].set_xlabel("Cosine Similarity")
        axes[1].set_ylabel("Count")
        axes[1].set_title("Cosine Similarity Distribution")
        axes[1].legend(); axes[1].grid(alpha=0.3)

        plt.suptitle("Embedding Space Analysis -- 128-D Face Vectors",
                     fontsize=13, fontweight="bold")
        plt.tight_layout()
        path = OUTPUT_DIR / "embedding_similarity.png"
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"  [OK] Saved: {path}")

    return {
        "cosine_genuine_mean"   : float(np.mean(gen_cos))  if gen_cos.size  else 0.0,
        "cosine_impostor_mean"  : float(np.mean(imp_cos))  if imp_cos.size  else 0.0,
        "euclidean_genuine_mean": float(np.mean(gen_euc))  if gen_euc.size  else 0.0,
        "euclidean_impostor_mean":float(np.mean(imp_euc))  if imp_euc.size  else 0.0,
        "rmse_genuine"          : rmse_gen,
        "rmse_impostor"         : rmse_imp,
    }


# =============================================================================
#  STEP 5  Summary Report
# =============================================================================

def print_summary(clf, ver, emb):
    print("\n" + SEP)
    print("  FINAL SUMMARY REPORT")
    print(SEP)

    if clf:
        print("\n  [CLASSIFICATION TASK]")
        print(f"    Accuracy   : {clf['accuracy']*100:.2f}%")
        print(f"    Precision  : {clf['precision']*100:.2f}%")
        print(f"    Recall     : {clf['recall']*100:.2f}%")
        print(f"    F1 Score   : {clf['f1']*100:.2f}%")
        print(f"    Unknown %  : {clf['unknown_rate']*100:.2f}%")

    if ver:
        print("\n  [VERIFICATION TASK]")
        print(f"    AUC        : {ver['auc']:.4f}")
        print(f"    EER        : {ver['eer']*100:.2f}%")
        print(f"    FAR        : {ver['far']*100:.2f}%")
        print(f"    FRR        : {ver['frr']*100:.2f}%")

    if emb:
        print("\n  [EMBEDDING SIMILARITY]")
        print(f"    Cosine Sim  (genuine)  : {emb['cosine_genuine_mean']:.4f}")
        print(f"    Cosine Sim  (impostor) : {emb['cosine_impostor_mean']:.4f}")
        print(f"    Euclidean   (genuine)  : {emb['euclidean_genuine_mean']:.4f}")
        print(f"    Euclidean   (impostor) : {emb['euclidean_impostor_mean']:.4f}")
        print(f"    RMSE genuine  (vs 0)   : {emb['rmse_genuine']:.4f}")
        print(f"    RMSE impostor (vs 1)   : {emb['rmse_impostor']:.4f}")

    if HAS_MATPLOTLIB:
        print(f"\n  All plots saved to: {OUTPUT_DIR.resolve()}")

    print("\n" + SEP + "\n")


# =============================================================================
#  MAIN
# =============================================================================

if __name__ == "__main__":
    encodings, labels, names = load_dataset()

    if len(encodings) == 0:
        print("\nERROR: No face encodings loaded. "
              "Check that dataset folders contain valid images.\n")
        sys.exit(1)

    clf = evaluate_classification(encodings, labels, names)
    ver = evaluate_verification(encodings, labels)
    emb = evaluate_embeddings(encodings, labels)

    print_summary(clf, ver, emb)
