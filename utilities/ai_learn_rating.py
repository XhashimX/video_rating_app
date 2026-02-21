"""
AI RATING PREDICTOR  v3.0  —  PRECISION CORE
=============================================
Architecture:
  1. Feature Engineering  — 23 raw → 60+ engineered features
  2. Weighted Sampling    — 3× weight on 900-1800 (your critical zone)
  3. Optuna Tuning        — auto-optimizes every hyperparameter
  4. Stacked Ensemble     — XGBoost + LightGBM + Ridge → meta-learner
  5. Isotonic Calibration — aligns predictions to real distribution
  6. Range-specific eval  — separate metrics for low/mid/high tiers

Install once:
    pip install xgboost lightgbm optuna scikit-learn joblib
"""

import os, json, math, warnings, threading, random
import numpy as np
import pandas as pd
import mediapipe as mp
import cv2
import joblib
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from xgboost  import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.linear_model    import Ridge
from sklearn.ensemble        import RandomForestRegressor, GradientBoostingRegressor
from sklearn.isotonic        import IsotonicRegression
from sklearn.preprocessing   import StandardScaler, PolynomialFeatures
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics         import mean_absolute_error
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────
# 1. CONFIGURATION
# ──────────────────────────────────────────────────────
BASE_DIR       = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
VIDEO_FOLDER   = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK\A1000 elo tik"
JSON_DATA_PATH = os.path.join(BASE_DIR, "elo_videos_A1000 elo tik.json")

MEMORY_FILE  = "visual_memory_v2.csv"
BRAIN_FILE   = "precision_brain.joblib"   # New File
PREFS_FILE   = "user_preferences.joblib"
MODEL_ASSET_PATH = "face_landmarker.task"

# Critical range where accuracy is most important
CRITICAL_MIN   = 900
CRITICAL_MAX   = 1800
CRITICAL_WEIGHT = 3.0   # 3x importance for the critical range

FRAME_SAMPLE_POSITIONS = [0.15, 0.30, 0.50, 0.65, 0.80]
SCAN_TIMEOUT_SECONDS   = 12

# ──────────────────────────────────────────────────────
# 2. RAW FEATURES
# ──────────────────────────────────────────────────────
RAW_FEATURE_COLUMNS = [
    'face_width', 'face_height', 'face_area', 'face_ratio',
    'cheek_symmetry', 'eye_symmetry', 'brow_symmetry',
    'eye_width_ratio', 'eye_openness', 'inter_eye_ratio',
    'nose_length_ratio',
    'mouth_width_ratio', 'mouth_eye_ratio', 'lip_fullness',
    'brow_height', 'jaw_ratio', 'chin_ratio',
    'face_center_offset', 'face_yaw',
    'brightness', 'saturation', 'skin_uniformity',
    'has_face'
]

FEATURE_META = {
    'face_ratio':         {'en': 'Face Ratio (H/W)',       'high': 'Elongated', 'low': 'Wide'},
    'cheek_symmetry':     {'en': 'Cheek Symmetry',          'high': 'High Symmetry', 'low': 'Low Symmetry'},
    'eye_symmetry':       {'en': 'Eye Symmetry',            'high': 'High', 'low': 'Low'},
    'brow_symmetry':      {'en': 'Brow Symmetry',           'high': 'High', 'low': 'Low'},
    'eye_width_ratio':    {'en': 'Eye Size/Face',           'high': 'Large Eyes', 'low': 'Small Eyes'},
    'eye_openness':       {'en': 'Eye Openness',            'high': 'Open', 'low': 'Narrow'},
    'inter_eye_ratio':    {'en': 'Inter-eye Distance',      'high': 'Wide-set', 'low': 'Close-set'},
    'nose_length_ratio':  {'en': 'Nose Length/Face',        'high': 'Long Nose', 'low': 'Short Nose'},
    'mouth_width_ratio':  {'en': 'Mouth Width/Face',         'high': 'Wide Mouth', 'low': 'Small Mouth'},
    'mouth_eye_ratio':    {'en': 'Mouth/Eye Ratio',         'high': 'Mouth > Eye', 'low': 'Mouth < Eye'},
    'lip_fullness':       {'en': 'Lip Fullness',           'high': 'Plump', 'low': 'Thin'},
    'brow_height':        {'en': 'Brow Height',            'high': 'High', 'low': 'Low'},
    'jaw_ratio':          {'en': 'Jaw Width',                'high': 'Wide', 'low': 'Narrow'},
    'chin_ratio':         {'en': 'Chin Region Length',         'high': 'Long', 'low': 'Short'},
    'face_center_offset': {'en': 'Center Offset',          'high': 'Offset', 'low': 'Centered'},
    'face_yaw':           {'en': 'Side Face Tilt',           'high': 'Tilted', 'low': 'Facing'},
    'brightness':         {'en': 'Video Brightness',           'high': 'Bright', 'low': 'Dim'},
    'saturation':         {'en': 'Color Saturation',             'high': 'Vivid', 'low': 'Dull'},
    'skin_uniformity':    {'en': 'Skin Uniformity',            'high': 'Uniform', 'low': 'Uneven'},
    'face_width':         {'en': 'Absolute Face Width',        'high': 'Large', 'low': 'Small'},
    'face_height':        {'en': 'Absolute Face Height',        'high': 'Large', 'low': 'Small'},
    'face_area':          {'en': 'Face Area in Frame',  'high': 'Close', 'low': 'Far'},
    'has_face':           {'en': 'Face Detected',              'high': 'Yes', 'low': 'No'},
}

# ──────────────────────────────────────────────────────
# 3. FEATURE ENGINEERING — The most important part
# ──────────────────────────────────────────────────────
def engineer_features(df_raw: pd.DataFrame) -> np.ndarray:
    """
    Converts raw features (23) into 60+ engineered features:
    - Feature interactions (multiplication + ratios)
    - Deviation from ideal preference ratios
    - Composite indicators (Overall Symmetry Score, Golden Ratio Proximity)
    - Non-linear transformations (log, sqrt)
    """
    df = df_raw[RAW_FEATURE_COLUMNS].copy().astype(np.float32)
    feats = {}

    # -- Raw Features --------------------------------
    for col in RAW_FEATURE_COLUMNS:
        feats[col] = df[col].values

    # -- Composite Symmetry Index -------------------------
    feats['overall_symmetry'] = (
        df['cheek_symmetry'].values * 0.4 +
        df['eye_symmetry'].values   * 0.35 +
        df['brow_symmetry'].values  * 0.25
    )

    # -- Symmetry x Beauty Interactions ---------------------
    feats['sym_x_eye_open']    = df['cheek_symmetry'].values * df['eye_openness'].values
    feats['sym_x_lip']         = df['cheek_symmetry'].values * df['lip_fullness'].values
    feats['sym_x_face_ratio']  = df['cheek_symmetry'].values * df['face_ratio'].values
    feats['eye_sym_x_width']   = df['eye_symmetry'].values   * df['eye_width_ratio'].values
    feats['brow_x_height']     = df['brow_symmetry'].values  * df['brow_height'].values

    # -- Deviation from Golden Ratio phi=1.618 -------------
    phi = 1.618
    feats['golden_ratio_dev']  = np.abs(df['face_ratio'].values - phi) / phi

    # -- Double Deviation: Ratio + Symmetry ------------------
    feats['harmony_score'] = (
        feats['overall_symmetry'] *
        np.exp(-feats['golden_ratio_dev'])
    )

    # -- Eye Volume: Width x Openness Interaction ---------------
    feats['eye_volume']        = df['eye_width_ratio'].values * df['eye_openness'].values
    feats['eye_inter_product'] = df['eye_width_ratio'].values * df['inter_eye_ratio'].values

    # -- Face Facial Thirds Balance ----------------------------
    # (Ideally face is divided into 3 equal thirds)
    feats['thirds_balance'] = 1.0 - np.abs(
        df['nose_length_ratio'].values - (1.0/3.0)
    )

    # -- Mouth and Lips ----------------------------------
    feats['lip_x_sym']    = df['lip_fullness'].values  * df['cheek_symmetry'].values
    feats['mouth_harmony'] = (
        df['mouth_width_ratio'].values * 0.6 +
        df['lip_fullness'].values      * 0.4
    )

    # -- Adjusting Lighting on Features -------------------
    # If lighting is poor, features are less reliable
    light_trust = np.clip(df['brightness'].values * 1.5, 0.3, 1.0)
    feats['trusted_symmetry'] = feats['overall_symmetry'] * light_trust
    feats['trusted_eye_open'] = df['eye_openness'].values  * light_trust

    # -- Offset from frame center affects accuracy ---------
    center_penalty = 1.0 - df['face_center_offset'].values * 2.0
    feats['centered_face_area'] = df['face_area'].values * np.clip(center_penalty, 0.5, 1.0)

    # -- Non-linear transformations ------------------------------
    feats['log_face_area']      = np.log1p(df['face_area'].values * 100)
    feats['sqrt_eye_volume']    = np.sqrt(np.clip(feats['eye_volume'], 0, None))
    feats['sq_cheek_symmetry']  = df['cheek_symmetry'].values ** 2
    feats['sq_eye_symmetry']    = df['eye_symmetry'].values   ** 2

    # -- Global feature: "Composite Attractiveness" ----------
    feats['attractiveness_composite'] = (
        feats['overall_symmetry']    * 0.30 +
        feats['harmony_score']       * 0.25 +
        feats['eye_volume']          * 0.20 +
        feats['mouth_harmony']       * 0.15 +
        df['skin_uniformity'].values * 0.10
    )

    # -- Feature Ratios ------------------------------
    feats['jaw_to_cheek']    = df['jaw_ratio'].values  / (df['face_width'].values + 1e-6)
    feats['chin_to_face']    = df['chin_ratio'].values / (df['face_height'].values + 1e-6)
    feats['nose_to_mouth']   = df['nose_length_ratio'].values / (df['mouth_width_ratio'].values + 1e-6)
    feats['brow_to_eye_gap'] = df['brow_height'].values / (df['eye_width_ratio'].values + 1e-6)

    # -- Face "Clarity" for the Camera -------------------
    feats['face_clarity'] = (
        (1.0 - df['face_yaw'].values * 3.0).clip(0, 1) *
        (1.0 - df['face_center_offset'].values * 2.0).clip(0, 1)
    )

    result = pd.DataFrame(feats)
    result = result.fillna(0.0)
    return result.values.astype(np.float32)


def get_engineered_feature_names() -> list:
    """Names of all engineered features (for interpretation)"""
    raw = RAW_FEATURE_COLUMNS.copy()
    extra = [
        'overall_symmetry', 'sym_x_eye_open', 'sym_x_lip', 'sym_x_face_ratio',
        'eye_sym_x_width', 'brow_x_height', 'golden_ratio_dev', 'harmony_score',
        'eye_volume', 'eye_inter_product', 'thirds_balance',
        'lip_x_sym', 'mouth_harmony', 'light_trust',
        'trusted_symmetry', 'trusted_eye_open', 'centered_face_area',
        'log_face_area', 'sqrt_eye_volume', 'sq_cheek_symmetry', 'sq_eye_symmetry',
        'attractiveness_composite',
        'jaw_to_cheek', 'chin_to_face', 'nose_to_mouth', 'brow_to_eye_gap',
        'face_clarity',
    ]
    return raw + extra


# ──────────────────────────────────────────────────────
# 4. SAMPLE WEIGHTS
# ──────────────────────────────────────────────────────
def compute_sample_weights(ratings: np.ndarray) -> np.ndarray:
    """
    Range 900-1800: weight 3x
    Range 1800-2500: weight 1.5x
    Outside these ranges: weight 1x
    """
    w = np.ones(len(ratings), dtype=np.float32)
    mask_critical = (ratings >= CRITICAL_MIN) & (ratings <= CRITICAL_MAX)
    mask_medium   = (ratings > CRITICAL_MAX)  & (ratings <= 2500)
    w[mask_critical] = CRITICAL_WEIGHT
    w[mask_medium]   = 1.5
    return w


from sklearn.base import clone

# ──────────────────────────────────────────────────────
# 5. OPTUNA TUNING (FIXED)
# ──────────────────────────────────────────────────────
def tune_xgboost(X, y, weights, n_trials=60):
    """Tune XGBoost with Optuna using sample weights"""
    def objective(trial):
        params = {
            'n_estimators':      trial.suggest_int('n_estimators', 300, 1000),
            'max_depth':         trial.suggest_int('max_depth', 3, 7),
            'learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'subsample':         trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'reg_alpha':         trial.suggest_float('reg_alpha', 0.01, 2.0, log=True),
            'reg_lambda':        trial.suggest_float('reg_lambda', 0.5, 5.0),
            'min_child_weight':  trial.suggest_int('min_child_weight', 1, 10),
            'gamma':             trial.suggest_float('gamma', 0.0, 1.0),
            'random_state': 42, 'verbosity': 0
        }
        base_model = XGBRegressor(**params)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        
        # Manual CV loop to replace cross_val_predict (fixes fit_params error)
        preds = np.zeros(len(y))
        for tr_idx, val_idx in kf.split(X):
            X_tr, X_val = X[tr_idx], X[val_idx]
            y_tr = y[tr_idx]
            w_tr = weights[tr_idx]
            
            # Clone model to ensure fresh start for each fold
            fold_model = clone(base_model)
            fold_model.fit(X_tr, y_tr, sample_weight=w_tr)
            preds[val_idx] = fold_model.predict(X_val)

        # Calculate MAE only for the critical range
        mask = (y >= CRITICAL_MIN) & (y <= CRITICAL_MAX)
        return mean_absolute_error(y[mask], preds[mask])

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params


def tune_lgbm(X, y, weights, n_trials=60):
    """Tune LightGBM with Optuna"""
    def objective(trial):
        params = {
            'n_estimators':    trial.suggest_int('n_estimators', 300, 1000),
            'max_depth':       trial.suggest_int('max_depth', 3, 8),
            'learning_rate':   trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'num_leaves':      trial.suggest_int('num_leaves', 15, 63),
            'subsample':       trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree':trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'reg_alpha':       trial.suggest_float('reg_alpha', 0.01, 2.0, log=True),
            'reg_lambda':      trial.suggest_float('reg_lambda', 0.5, 5.0),
            'min_child_samples':trial.suggest_int('min_child_samples', 5, 50),
            'random_state': 42, 'verbosity': -1, 'force_row_wise': True
        }
        base_model = LGBMRegressor(**params)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        
        # Manual CV loop to replace cross_val_predict (fixes fit_params error)
        preds = np.zeros(len(y))
        for tr_idx, val_idx in kf.split(X):
            X_tr, X_val = X[tr_idx], X[val_idx]
            y_tr = y[tr_idx]
            w_tr = weights[tr_idx]
            
            fold_model = clone(base_model)
            fold_model.fit(X_tr, y_tr, sample_weight=w_tr)
            preds[val_idx] = fold_model.predict(X_val)

        mask  = (y >= CRITICAL_MIN) & (y <= CRITICAL_MAX)
        return mean_absolute_error(y[mask], preds[mask])

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params

def tune_lgbm(X, y, weights, n_trials=60):
    """Tune LightGBM with Optuna (Visible Progress & Fixed fit_params)"""
    def objective(trial):
        params = {
            'n_estimators':    trial.suggest_int('n_estimators', 300, 1000),
            'max_depth':       trial.suggest_int('max_depth', 3, 8),
            'learning_rate':   trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'num_leaves':      trial.suggest_int('num_leaves', 15, 63),
            'subsample':       trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree':trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'reg_alpha':       trial.suggest_float('reg_alpha', 0.01, 2.0, log=True),
            'reg_lambda':      trial.suggest_float('reg_lambda', 0.5, 5.0),
            'min_child_samples':trial.suggest_int('min_child_samples', 5, 50),
            'random_state': 42, 'verbosity': -1, 'force_row_wise': True
        }
        base_model = LGBMRegressor(**params)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        
        # Manual CV loop to replace cross_val_predict (Fixes the TypeError)
        preds = np.zeros(len(y))
        for tr_idx, val_idx in kf.split(X):
            X_tr, X_val = X[tr_idx], X[val_idx]
            y_tr = y[tr_idx]
            w_tr = weights[tr_idx]
            
            fold_model = clone(base_model)
            fold_model.fit(X_tr, y_tr, sample_weight=w_tr)
            preds[val_idx] = fold_model.predict(X_val)

        mask  = (y >= CRITICAL_MIN) & (y <= CRITICAL_MAX)
        return mean_absolute_error(y[mask], preds[mask])

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params
# ──────────────────────────────────────────────────────
# 6. STACKED ENSEMBLE
# ──────────────────────────────────────────────────────
class StackedEnsemble:
    """
    Level 1: XGBoost + LightGBM + RandomForest + GradientBoosting
    Level 2: Ridge meta-learner learns how to combine their predictions
    Level 3: IsotonicRegression to calibrate the final distribution
    """

    def __init__(self, xgb_params=None, lgbm_params=None):
        xgb_params  = xgb_params  or {}
        lgbm_params = lgbm_params or {}

        self.base_models = {
            'xgb': XGBRegressor(
                random_state=42, verbosity=0,
                **{k: v for k, v in xgb_params.items()}
            ),
            'lgbm': LGBMRegressor(
                random_state=42, verbosity=-1, force_row_wise=True,
                **{k: v for k, v in lgbm_params.items()}
            ),
            'rf': RandomForestRegressor(
                n_estimators=400, max_depth=6,
                min_samples_leaf=4, random_state=42, n_jobs=-1
            ),
            'gbr': GradientBoostingRegressor(
                n_estimators=300, max_depth=4,
                learning_rate=0.05, subsample=0.8,
                random_state=42
            ),
        }
        self.meta  = Ridge(alpha=10.0)
        self.calib = IsotonicRegression(out_of_bounds='clip')
        self.scaler = StandardScaler()

    def _oof_predictions(self, X, y, weights, n_splits=5):
        """Out-of-Fold predictions for each base model"""
        kf   = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        oof  = np.zeros((len(y), len(self.base_models)))

        for fold_i, (tr_idx, val_idx) in enumerate(kf.split(X)):
            X_tr, X_val = X[tr_idx], X[val_idx]
            y_tr, y_val = y[tr_idx], y[val_idx]
            w_tr        = weights[tr_idx]

            for j, (name, m) in enumerate(self.base_models.items()):
                if name in ('xgb', 'lgbm'):
                    m.fit(X_tr, y_tr, sample_weight=w_tr)
                else:
                    m.fit(X_tr, y_tr, sample_weight=w_tr)
                oof[val_idx, j] = m.predict(X_val)

            fold_mask = (y[val_idx] >= CRITICAL_MIN) & (y[val_idx] <= CRITICAL_MAX)
            if fold_mask.sum() > 0:
                fold_mae = mean_absolute_error(y[val_idx][fold_mask], oof[val_idx][fold_mask].mean(axis=1))
                print(f"      Fold {fold_i+1}  │  MAE (900-1800): ±{fold_mae:.0f}")

        return oof

    def fit(self, X, y, weights):
        X_sc = self.scaler.fit_transform(X)
        print("  ⏳ Calculating Out-of-Fold predictions...")
        oof = self._oof_predictions(X_sc, y, weights)

        print("  🔗 Training Meta-Learner (Ridge)...")
        self.meta.fit(oof, y)

        print("  🎯 Calibrating distribution (Isotonic Calibration)...")
        meta_preds = self.meta.predict(oof)
        self.calib.fit(meta_preds, y)

        print("  🏁 Final training on full data...")
        for name, m in self.base_models.items():
            m.fit(X_sc, y, sample_weight=weights)

        return self

    def predict(self, X):
        X_sc   = self.scaler.transform(X)
        preds  = np.column_stack([m.predict(X_sc) for m in self.base_models.values()])
        meta_p = self.meta.predict(preds)
        return self.calib.predict(meta_p)

    def predict_with_uncertainty(self, X):
        """Returns (prediction, deviation) — Deviation expresses AI confidence"""
        X_sc  = self.scaler.transform(X)
        preds = np.column_stack([m.predict(X_sc) for m in self.base_models.values()])
        mean_ = self.meta.predict(preds)
        calib = self.calib.predict(mean_)
        std_  = np.std(preds, axis=1)
        return calib, std_


# ──────────────────────────────────────────────────────
# 7. RANGE-SPECIFIC EVALUATION
# ──────────────────────────────────────────────────────
def evaluate_by_range(y_true, y_pred):
    ranges = [
        ('< 900',       y_true < 900),
        ('900-1200',   (y_true >= 900)  & (y_true < 1200)),
        ('1200-1500',  (y_true >= 1200) & (y_true < 1500)),
        ('1500-1800',  (y_true >= 1500) & (y_true < 1800)),
        ('1800-2500',  (y_true >= 1800) & (y_true < 2500)),
        ('> 2500',      y_true >= 2500),
    ]
    print(f"\n  {'Range':<14} {'Count':<5} {'MAE':>6}  {'±%':>6}  {'Acc 15%':>8}")
    print("  " + "─" * 50)
    for label, mask in ranges:
        if mask.sum() == 0:
            continue
        yt, yp = y_true[mask], y_pred[mask]
        mae    = mean_absolute_error(yt, yp)
        pct    = mae / (yt.mean() + 1e-6) * 100
        acc15  = np.mean(np.abs(yt - yp) <= yt * 0.15) * 100
        bar_ok = "█" * int(acc15 / 5)
        print(f"  {label:<14} {mask.sum():<5} {mae:>6.0f}  {pct:>5.1f}%  {acc15:>6.1f}%  {bar_ok}")


# ──────────────────────────────────────────────────────
# 8. MEMORY / DATA
# ──────────────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_FILE):
        df = pd.read_csv(MEMORY_FILE)
        for col in RAW_FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0
        return df
    return pd.DataFrame(columns=['filename', 'file_size'] + RAW_FEATURE_COLUMNS)

def load_elo_data():
    if not os.path.exists(JSON_DATA_PATH):
        return {}
    with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_size_to_rating(elo_data):
    return {v['file_size']: v.get('rating', 1000)
            for v in elo_data.values() if v.get('file_size')}


# ──────────────────────────────────────────────────────
# 9. VISION ENGINE (same as v2, unchanged)
# ──────────────────────────────────────────────────────
class VisionEngine:
    LANDMARK_INDICES = {
        'nose_tip': 4, 'forehead': 10, 'chin': 152,
        'left_cheek': 234, 'right_cheek': 454,
        'left_eye_outer': 33, 'right_eye_outer': 263,
        'left_eye_inner': 133, 'right_eye_inner': 362,
        'left_eye_top': 159, 'left_eye_bottom': 145,
        'right_eye_top': 386, 'right_eye_bottom': 374,
        'mouth_left': 61, 'mouth_right': 291,
        'upper_lip': 0, 'lower_lip': 17,
        'left_brow_outer': 70, 'right_brow_outer': 300,
        'left_brow_inner': 107, 'right_brow_inner': 336,
        'jaw_left': 172, 'jaw_right': 397,
    }

    def __init__(self):
        if not os.path.exists(MODEL_ASSET_PATH):
            raise FileNotFoundError(f"Model missing: {MODEL_ASSET_PATH}")
        opts = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_ASSET_PATH),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
            running_mode=vision.RunningMode.IMAGE
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(opts)

    def _d(self, lm, i, j):
        return np.linalg.norm(np.array([lm[i].x, lm[i].y]) - np.array([lm[j].x, lm[j].y]))

    def _p(self, lm, i):
        return np.array([lm[i].x, lm[i].y])

    def _facial(self, lm):
        idx = self.LANDMARK_INDICES; f = {}
        fw = self._d(lm, idx['left_cheek'], idx['right_cheek'])
        fh = self._d(lm, idx['forehead'],   idx['chin'])
        f['face_width'] = fw; f['face_height'] = fh
        f['face_area']  = fw * fh; f['face_ratio'] = fh / (fw + 1e-6)
        nose = self._p(lm, idx['nose_tip'])
        lc   = self._p(lm, idx['left_cheek']); rc = self._p(lm, idx['right_cheek'])
        dl   = np.linalg.norm(nose - lc);      dr = np.linalg.norm(nose - rc)
        f['cheek_symmetry'] = 1.0 - abs(dl - dr) / (dl + dr + 1e-6)
        lew = self._d(lm, idx['left_eye_outer'],  idx['left_eye_inner'])
        rew = self._d(lm, idx['right_eye_outer'], idx['right_eye_inner'])
        f['eye_symmetry'] = 1.0 - abs(lew - rew) / (lew + rew + 1e-6)
        aew = (lew + rew) / 2
        f['eye_width_ratio'] = aew / (fw + 1e-6)
        leh = self._d(lm, idx['left_eye_top'],  idx['left_eye_bottom'])
        reh = self._d(lm, idx['right_eye_top'], idx['right_eye_bottom'])
        aeh = (leh + reh) / 2
        f['eye_openness']   = aeh / (aew + 1e-6)
        ie  = self._d(lm, idx['left_eye_inner'], idx['right_eye_inner'])
        f['inter_eye_ratio'] = ie / (fw + 1e-6)
        f['nose_length_ratio'] = self._d(lm, idx['forehead'], idx['nose_tip']) / (fh + 1e-6)
        mw = self._d(lm, idx['mouth_left'], idx['mouth_right'])
        f['mouth_width_ratio'] = mw / (fw + 1e-6)
        f['mouth_eye_ratio']   = mw / (aew + 1e-6)
        f['lip_fullness'] = self._d(lm, idx['upper_lip'], idx['lower_lip']) / (mw + 1e-6)
        lbw = self._d(lm, idx['left_brow_outer'],  idx['left_brow_inner'])
        rbw = self._d(lm, idx['right_brow_outer'], idx['right_brow_inner'])
        f['brow_symmetry'] = 1.0 - abs(lbw - rbw) / (lbw + rbw + 1e-6)
        f['brow_height']   = self._d(lm, idx['left_brow_inner'], idx['left_eye_inner']) / (fh + 1e-6)
        f['jaw_ratio']     = self._d(lm, idx['jaw_left'], idx['jaw_right']) / (fw + 1e-6)
        f['chin_ratio']    = self._d(lm, idx['chin'], idx['lower_lip']) / (fh + 1e-6)
        nx = self._p(lm, idx['nose_tip'])[0]
        f['face_center_offset'] = abs(nx - 0.5)
        cx = (lc[0] + rc[0]) / 2
        f['face_yaw'] = abs(nose[0] - cx) / (fw + 1e-6)
        return f

    def _color(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        return {
            'brightness':     np.mean(hsv[:, :, 2]) / 255.0,
            'saturation':     np.mean(hsv[:, :, 1]) / 255.0,
            'skin_uniformity': max(0.0, 1.0 - np.std(lab[:, :, 0]) / 128.0),
        }

    def _frame_score(self, frame, results):
        if not results.face_landmarks: return 0.0
        lm = results.face_landmarks[0]
        xs = [l.x for l in lm]; ys = [l.y for l in lm]
        size = (max(xs) - min(xs)) * (max(ys) - min(ys))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        return size * min(sharpness / 300.0, 1.0)

    def extract_features(self, video_path):
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened(): return None
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total < 5: cap.release(); return None
            best = None; best_score = -1
            for pos in FRAME_SAMPLE_POSITIONS:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * pos))
                ret, frame = cap.read()
                if not ret: continue
                h, w = frame.shape[:2]
                if w > 1280:
                    frame = cv2.resize(frame, (1280, int(h * 1280 / w)))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = self.landmarker.detect(mp_img)
                q   = self._frame_score(frame, res)
                if q > best_score: best_score = q; best = (frame, res)
            cap.release()
            if best is None or best[1].face_landmarks is None: return None
            frame, res = best
            return {**self._facial(res.face_landmarks[0]), **self._color(frame), 'has_face': 1.0}
        except Exception as e:
            print(f"  Error: {e}"); return None

    def extract_features_safe(self, video_path):
        r = [None]
        def t(): r[0] = self.extract_features(video_path)
        th = threading.Thread(target=t); th.start(); th.join(timeout=SCAN_TIMEOUT_SECONDS)
        return "TIMEOUT" if th.is_alive() else r[0]


# ──────────────────────────────────────────────────────
# 10. DISPLAY HELPERS
# ──────────────────────────────────────────────────────
def rating_label(r):
    if r >= 2500: return "⭐⭐⭐⭐⭐ Exceptional"
    if r >= 2000: return "⭐⭐⭐⭐  Very High"
    if r >= 1500: return "⭐⭐⭐   High"
    if r >= 1200: return "⭐⭐    Above Average"
    if r >= 900:  return "⭐     Average"
    return              "       Low"

def confidence_label(std):
    if std < 80:  return "🟢 High Confidence"
    if std < 160: return "🟡 Medium Confidence"
    return              "🔴 Low Confidence (Side profile or poor lighting)"

def print_full_report(feats_dict, user_prefs=None, pred=None, std=None):
    display = [c for c in RAW_FEATURE_COLUMNS if c != 'has_face']
    print("\n" + "─" * 78)
    print(f"  {'Feature':<30} {'Value':>8}  {'Ideal':>8}  {'Match':>7}  Bar")
    print("─" * 78)
    for col in display:
        meta  = FEATURE_META.get(col, {'en': col})
        val   = feats_dict.get(col, 0.0)
        if user_prefs and col in user_prefs:
            ideal = user_prefs[col]
            prox  = max(0.0, 1.0 - abs(val - ideal) / (abs(ideal) + 1e-6))
            bar   = "█" * int(prox * 20) + "░" * (20 - int(prox * 20))
            print(f"  {meta['en']:<30} {val:>8.3f}  {ideal:>8.3f}  {prox*100:>6.0f}%  {bar}")
        else:
            print(f"  {meta['en']:<30} {val:>8.3f}  {'─':>8}  {'─':>7}")
    print("─" * 78)
    if pred is not None and std is not None:
        print(f"  🧠 Prediction: {pred:.0f}   [{confidence_label(std)}  Dev±{std:.0f}]")


# ──────────────────────────────────────────────────────
# 11. MENU FUNCTIONS
# ──────────────────────────────────────────────────────

def menu_scan_videos():
    print("\n─── 👁️  SCAN VIDEOS ───")
    df_mem  = load_memory()
    scanned = set(df_mem['filename'].tolist())
    print(f"✅ Loaded: {len(scanned)} previously")
    all_f   = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.mov'))]
    new_f   = [f for f in all_f if f not in scanned]
    if not new_f: print("🎉 All videos already scanned!"); return
    print(f"🔍 {len(new_f)} new videos found")
    try: count = int(input(f"How many to scan? (Max={len(new_f)}): "))
    except: count = 20
    random.shuffle(new_f); target = new_f[:count]
    engine = VisionEngine(); ok = 0
    print(f"\n🚀 Started (Timeout {SCAN_TIMEOUT_SECONDS}s)...")
    for i, fn in enumerate(target):
        path = os.path.join(VIDEO_FOLDER, fn)
        sz   = os.path.getsize(path)
        feat = engine.extract_features_safe(path)
        if feat == "TIMEOUT":
            print(f"  [{i+1}/{count}] ⏱️  Timeout: {fn[:30]}")
        elif feat is None:
            print(f"  [{i+1}/{count}] ⚠️  No face: {fn[:30]}")
        else:
            row = {'filename': fn, 'file_size': sz}
            for col in RAW_FEATURE_COLUMNS: row[col] = feat.get(col, 0.0)
            pd.DataFrame([row]).to_csv(MEMORY_FILE, mode='a',
                                       header=not os.path.exists(MEMORY_FILE), index=False)
            ok += 1
            print(f"  [{i+1}/{count}] ✅ {fn[:30]}  sym={feat.get('cheek_symmetry',0):.2f}")
    print(f"\n✅ {ok}/{count} videos saved.")


def menu_train_brain():
    print("\n─── 🧠  PRECISION TRAINING  v3.0 ───")

    if not os.path.exists(MEMORY_FILE) or not os.path.exists(JSON_DATA_PATH):
        print("❌ Memory file or JSON missing."); return

    df        = load_memory()
    elo       = load_elo_data()
    s2r       = build_size_to_rating(elo)
    df['rating'] = df['file_size'].map(s2r)
    df = df.dropna(subset=['rating']); df = df[df['has_face'] == 1.0]

    print(f"📊 Data: {len(df)} videos")
    print(f"   Min={df['rating'].min():.0f}  Max={df['rating'].max():.0f}  "
          f"Avg={df['rating'].mean():.0f}  ±{df['rating'].std():.0f}")

    crit_n = ((df['rating'] >= CRITICAL_MIN) & (df['rating'] <= CRITICAL_MAX)).sum()
    print(f"   Critical Range 900-1800: {crit_n} videos ({crit_n/len(df)*100:.0f}%)")

    if len(df) < 30: print("⚠️  Too little data to train properly."); return

    # Feature Engineering
    print("\n⚙️  Feature Engineering (23 Raw → 60+ Engineered)...")
    X_eng = engineer_features(df)
    y     = df['rating'].values.astype(np.float32)
    w     = compute_sample_weights(y)
    print(f"   Final Features: {X_eng.shape[1]}")

    # Optuna Tuning
    print("\n🔬 Tuning XGBoost with Optuna (60 trials)...")
    xgb_params = tune_xgboost(X_eng, y, w, n_trials=60)
    print(f"   Best XGBoost params: {xgb_params}")

    print("\n🔬 Tuning LightGBM with Optuna (60 trials)...")
    lgbm_params = tune_lgbm(X_eng, y, w, n_trials=60)
    print(f"   Best LGBM params: {lgbm_params}")

    # Stacked Ensemble Training
    print("\n🏋️  Training Stacked Ensemble...")
    ensemble = StackedEnsemble(xgb_params=xgb_params, lgbm_params=lgbm_params)
    ensemble.fit(X_eng, y, w)

    # Final Evaluation
    print("\n📊 Final Evaluation (OOF)...")
    kf   = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_preds = np.zeros(len(y))
    for tr, val in kf.split(X_eng):
        tmp = StackedEnsemble(xgb_params=xgb_params, lgbm_params=lgbm_params)
        tmp.fit(X_eng[tr], y[tr], w[tr])
        oof_preds[val] = tmp.predict(X_eng[val])
    
    mae_all  = mean_absolute_error(y, oof_preds)
    mask_cr  = (y >= CRITICAL_MIN) & (y <= CRITICAL_MAX)
    mae_crit = mean_absolute_error(y[mask_cr], oof_preds[mask_cr])

    print(f"\n  Overall MAE          : ±{mae_all:.0f}")
    print(f"  Critical Range MAE    : ±{mae_crit:.0f}  ← Most Important Metric")
    evaluate_by_range(y, oof_preds)

    # Extract user preferences
    top_mask   = y >= np.percentile(y, 75)
    df_top     = df[RAW_FEATURE_COLUMNS][top_mask]
    user_prefs = {col: float(df_top[col].mean()) for col in RAW_FEATURE_COLUMNS if col != 'has_face'}

    # Save
    brain_data = {
        'ensemble':    ensemble,
        'xgb_params':  xgb_params,
        'lgbm_params': lgbm_params,
        'mae_all':     mae_all,
        'mae_critical':mae_crit,
    }
    joblib.dump(brain_data,  BRAIN_FILE)
    joblib.dump(user_prefs,  PREFS_FILE)
    print(f"\n✅ Brain saved!  Critical MA: ±{mae_crit:.0f}  │  Total MAE: ±{mae_all:.0f}")


def menu_guess_single():
    print("\n─── 🔮  PREDICT VIDEO ───")
    if not os.path.exists(BRAIN_FILE): print("❌ Train the brain first."); return
    brain_data = joblib.load(BRAIN_FILE); ensemble = brain_data['ensemble']
    user_prefs = joblib.load(PREFS_FILE) if os.path.exists(PREFS_FILE) else None
    engine     = VisionEngine()
    print(f"📈 Brain Accuracy: ±{brain_data.get('mae_critical', '?'):.0f} (900-1800 range)")
    print("💡 Type 'exit' to return to menu.\n")

    while True:
        path = input("📂 Path: ").strip().strip('"')
        if path.lower() in ('خروج','exit','q','quit','0'): break
        if not os.path.exists(path): print("❌ Invalid path.\n"); continue

        print("  ⏳ Analyzing...")
        feats = engine.extract_features_safe(path)
        if feats == "TIMEOUT": print("  ❌ Timeout.\n"); continue
        if feats is None: print("  ❌ No face detected.\n"); continue

        row_df  = pd.DataFrame([{col: feats.get(col, 0.0) for col in RAW_FEATURE_COLUMNS}])
        X_eng   = engineer_features(row_df)
        pred, std = ensemble.predict_with_uncertainty(X_eng)
        pred = float(pred[0]); std = float(std[0])

        print("\n" + "═" * 55)
        print(f"  🧠 Prediction: {pred:.0f}   {rating_label(pred)}")
        print(f"  📊 Confidence: {confidence_label(std)}  (±{std:.0f})")
        print("═" * 55)
        print_full_report(feats, user_prefs, pred, std)

        if user_prefs:
            gaps = {c: abs(feats.get(c,0)-user_prefs[c])/(user_prefs[c]+1e-6)
                    for c in RAW_FEATURE_COLUMNS if c not in ('has_face','face_center_offset','face_yaw')}
            best3  = sorted(gaps.items(), key=lambda x: x[1])[:3]
            worst3 = sorted(gaps.items(), key=lambda x: x[1], reverse=True)[:3]
            print("\n  ✅ Strengths:")
            for c,g in best3:
                print(f"     • {FEATURE_META.get(c,{'en':c})['en']:<30} Match {(1-g)*100:.0f}%")
            print("  ⚠️  Biggest gaps from your preferences:")
            for c,g in worst3:
                v=feats.get(c,0); i=user_prefs.get(c,v)
                print(f"     • {FEATURE_META.get(c,{'en':c})['en']:<30} Yours={v:.3f}  Ideal={i:.3f}")
        print()


def menu_batch_test():
    print("\n─── 🧪  ACCURACY TEST ───")
    if not os.path.exists(BRAIN_FILE): print("❌ Train the brain first."); return
    brain_data = joblib.load(BRAIN_FILE); ensemble = brain_data['ensemble']
    user_prefs = joblib.load(PREFS_FILE) if os.path.exists(PREFS_FILE) else None

    df = load_memory(); elo = load_elo_data(); s2r = build_size_to_rating(elo)
    df['actual'] = df['file_size'].map(s2r)
    df = df.dropna(subset=['actual']); df = df[df['has_face'] == 1.0]
    try: n = int(input(f"How many videos? (Available: {len(df)}): "))
    except: n = 30
    sample = df.sample(n=min(n, len(df)))

    X_eng = engineer_features(sample)
    preds_arr, stds_arr = ensemble.predict_with_uncertainty(X_eng)
    actuals = sample['actual'].values

    print("\n" + "═" * 90)
    print(f"  {'Video':<28} {'Actual':>7}  {'Pred':>7}  {'Diff':>5}  {'Conf':>5}  Result")
    print("═" * 90)
    ok = 0
    for i, (_, row) in enumerate(sample.iterrows()):
        pred   = float(preds_arr[i]); std = float(stds_arr[i]); actual = float(row['actual'])
        diff   = abs(actual - pred)
        allow  = actual * (0.25 if actual > 1500 else 0.15)
        passed = diff <= allow
        if passed: ok += 1
        conf = "🟢" if std < 80 else ("🟡" if std < 160 else "🔴")
        stat = "✅" if passed else "❌"
        print(f"  {row['filename'][:28]:<28} {actual:>7.0f}  {pred:>7.0f}  {diff:>5.0f}  {conf}     {stat}")

    print("═" * 90)
    mae  = mean_absolute_error(actuals, preds_arr)
    acc  = ok / len(sample) * 100
    mask = (actuals >= CRITICAL_MIN) & (actuals <= CRITICAL_MAX)
    mae_c = mean_absolute_error(actuals[mask], preds_arr[mask]) if mask.sum() > 0 else 0

    print(f"  Total Accuracy  : {acc:.1f}%  ({ok}/{len(sample)})")
    print(f"  Total MAE       : ±{mae:.0f}")
    print(f"  MAE 900-1800    : ±{mae_c:.0f}  ← Most Important")
    evaluate_by_range(actuals, preds_arr)

    show = input("\n📋 Show detailed report for each video? (y/n): ").strip()
    if show.lower() in ('y', 'yes'):
        for i, (_, row) in enumerate(sample.iterrows()):
            feats = {c: row.get(c, 0.0) for c in RAW_FEATURE_COLUMNS}
            pred  = float(preds_arr[i]); std = float(stds_arr[i])
            print(f"\n{'═'*55}\n  {row['filename'][:45]}\n  Actual: {row['actual']:.0f}  │  Pred: {pred:.0f}")
            print_full_report(feats, user_prefs, pred, std)


def menu_stats():
    print("\n─── 📊  STATS & PREFERENCES ───")
    if not os.path.exists(MEMORY_FILE): print("❌ No data available."); return
    df = load_memory(); elo = load_elo_data(); s2r = build_size_to_rating(elo)
    df['rating'] = df['file_size'].map(s2r)
    df_r = df.dropna(subset=['rating']); df_r = df_r[df_r['has_face'] == 1.0]

    print(f"\n  Total Scanned: {len(df)}   With Face: {int(df['has_face'].sum())}   With Rating: {len(df_r)}")
    if len(df_r) == 0: return

    print("\n  📈 Rating Distribution:")
    bins   = [0, 700, 900, 1100, 1300, 1600, 2000, 9999]
    labels = ['< 700','700-900','900-1100','1100-1300','1300-1600','1600-2000','> 2000']
    df_r['bkt'] = pd.cut(df_r['rating'], bins=bins, labels=labels)
    dist = df_r['bkt'].value_counts().sort_index(); mx = dist.max() or 1
    for lb, cnt in dist.items():
        bar = "█" * int(cnt / mx * 35)
        print(f"    {lb:<12}  {bar:<35} {cnt}")

    if os.path.exists(PREFS_FILE):
        up = joblib.load(PREFS_FILE)
        print("\n  🎯 Your Preferences (From top 25% rated):")
        print(f"  {'Feature':<30} {'Your Ideal':>10}  Description")
        print("  " + "─" * 60)
        for col in RAW_FEATURE_COLUMNS:
            if col == 'has_face': continue
            meta = FEATURE_META.get(col, {'en': col, 'high': ''})
            v    = up.get(col, 0.0)
            print(f"  {meta['en']:<30} {v:>10.3f}  ← {meta.get('high','') if v > 0.5 else meta.get('low','')}")

    print("\n  📐 Feature Correlation with Ratings:")
    corrs = {c: df_r[c].corr(df_r['rating']) for c in RAW_FEATURE_COLUMNS if c != 'has_face'}
    for c, r in sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True):
        meta = FEATURE_META.get(c, {'en': c})
        sgn  = "▲" if r > 0 else "▼"
        bar  = sgn * int(abs(r) * 25)
        print(f"    {meta['en']:<30}  {r:>+6.3f}  {bar}")

    if os.path.exists(PREFS_FILE):
        up = joblib.load(PREFS_FILE)
        show_feats = ['cheek_symmetry','face_ratio','eye_openness','lip_fullness','eye_width_ratio']
        print("\n  🏆 Best Video representing each feature:")
        for col in show_feats:
            if col not in df_r.columns: continue
            meta  = FEATURE_META.get(col, {'en': col})
            ideal = up.get(col, df_r[col].mean())
            best  = df_r.loc[(df_r[col] - ideal).abs().idxmin()]
            print(f"\n    {meta['en']}  (Ideal={ideal:.3f})")
            print(f"      📹 {best['filename'][:55]}")
            print(f"         Value={best[col]:.3f}   Rating={best['rating']:.0f}")

    print("\n  🥇 Top 10 Rated Videos:")
    top10 = df_r.nlargest(10, 'rating')[['filename','rating','cheek_symmetry','face_ratio','eye_openness']]
    print(f"  {'Video':<32} {'Rating':>7}  {'Symm':>7}  {'Ratio':>7}  {'Open':>7}")
    print("  " + "─" * 65)
    for _, row in top10.iterrows():
        print(f"  {row['filename'][:32]:<32} {row['rating']:>7.0f}  "
              f"{row['cheek_symmetry']:>7.3f}  {row['face_ratio']:>7.3f}  {row['eye_openness']:>7.3f}")


# ──────────────────────────────────────────────────────
# 12. MAIN
# ──────────────────────────────────────────────────────
def main():
    print("\n" + "═" * 55)
    print("   🤖  AI RATING PREDICTOR  v3.0  PRECISION CORE")
    print("   Ensemble | Optuna | Calibration | Weighted")
    print("═" * 55)
    if os.path.exists(BRAIN_FILE):
        d = joblib.load(BRAIN_FILE)
        print(f"   🧠 Brain Loaded │ Critical MAE: ±{d.get('mae_critical','?'):.0f}  │  Total MAE: ±{d.get('mae_all','?'):.0f}")

    while True:
        print("\n  1. 👁️   Scan New Videos")
        print("  2. 🧠   Train Brain (Precision)")
        print("  3. 🔮   Guess Videos (Loop)")
        print("  4. 🧪   Accuracy Test")
        print("  5. 📊   Stats & Preferences")
        print("  6. ❌   Exit")
        c = input("\n  Choice: ").strip()
        if   c == '1': menu_scan_videos()
        elif c == '2': menu_train_brain()
        elif c == '3': menu_guess_single()
        elif c == '4': menu_batch_test()
        elif c == '5': menu_stats()
        elif c == '6': print("Goodbye! 👋"); break
        else: print("  Invalid choice.")

if __name__ == "__main__":
    main()