"""
Model Training Module for OLPA Project
Trains predictive maintenance models with MLflow tracking
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import logging
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from imblearn.over_sampling import SMOTE

from utils import MLflowManager, ModelEvaluator, TimeSeriesSplit

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MaintenancePredictor:
    """
    Main class for training predictive maintenance models
    """

    def __init__(self, data_path, config_path='config/mlflow_config.yaml'):
        """
        Initialize predictor

        Args:
            data_path: Path to processed sensor data
            config_path: Path to MLflow configuration
        """
        self.data_path = Path(data_path)
        self.mlflow_manager = MLflowManager(config_path)
        self.scaler = StandardScaler()

    def load_data(self):
        """Load and prepare data"""
        logger.info(f"Loading data from {self.data_path}")

        df = pd.read_csv(self.data_path, parse_dates=['date'])

        logger.info(f"Loaded {len(df)} records")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")

        return df

    def prepare_features(self, df, use_engineered=True):
        """
        Prepare features for modeling

        Args:
            df: DataFrame with sensor data
            use_engineered: Whether to use engineered features

        Returns:
            DataFrame with features and target
        """
        logger.info("Preparing features")

        target_col = 'will_fail_7days'

        if use_engineered:
            # Use all engineered features except identifiers and target
            exclude_cols = ['aircraft_id', 'date', 'cycle', 'failed',
                          'days_to_failure', 'will_fail_7days']
            feature_cols = [col for col in df.columns if col not in exclude_cols]
            logger.info(f"Using {len(feature_cols)} engineered features")
        else:
            # Basic sensor features only
            feature_cols = [
                'temperature', 'vibration', 'pressure', 'rpm',
                'altitude', 'ambient_temp', 'flight_hours'
            ]
            logger.info(f"Using {len(feature_cols)} basic features")

        # Check for missing values
        missing = df[feature_cols + [target_col]].isnull().sum().sum()
        if missing > 0:
            logger.warning(f"Found {missing} missing values. Dropping rows...")
            df = df.dropna(subset=feature_cols + [target_col])

        logger.info(f"Features: {len(feature_cols)} columns")
        logger.info(f"Target: {target_col}")

        return df, feature_cols, target_col

    def split_data(self, df, feature_cols, target_col):
        """
        Perform time-series aware train/val/test split

        Args:
            df: DataFrame
            feature_cols: List of feature columns
            target_col: Target column

        Returns:
            (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        logger.info("Splitting data with time-series awareness")

        splitter = TimeSeriesSplit(df, date_column='date', gap_days=7)
        train_df, val_df, test_df = splitter.split(
            train_ratio=0.7,
            val_ratio=0.15,
            test_ratio=0.15
        )

        # Extract features and targets
        X_train, y_train = splitter.get_xy(train_df, feature_cols, target_col)
        X_val, y_val = splitter.get_xy(val_df, feature_cols, target_col)
        X_test, y_test = splitter.get_xy(test_df, feature_cols, target_col)

        # Check class distribution
        train_pos = np.sum(y_train)
        val_pos = np.sum(y_val)
        test_pos = np.sum(y_test)

        logger.info(f"Train: {len(y_train)} samples, {train_pos} failures ({train_pos/len(y_train)*100:.2f}%)")
        logger.info(f"Validation: {len(y_val)} samples, {val_pos} failures ({val_pos/len(y_val)*100:.2f}%)")
        logger.info(f"Test: {len(y_test)} samples, {test_pos} failures ({test_pos/len(y_test)*100:.2f}%)")

        return X_train, X_val, X_test, y_train, y_val, y_test, feature_cols

    def scale_features(self, X_train, X_val, X_test):
        """
        Scale features using StandardScaler

        Args:
            X_train, X_val, X_test: Feature arrays

        Returns:
            Scaled feature arrays
        """
        logger.info("Scaling features")

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        return X_train_scaled, X_val_scaled, X_test_scaled

    def handle_class_imbalance(self, X_train, y_train, method='class_weight'):
        """
        Handle class imbalance

        Args:
            X_train: Training features
            y_train: Training labels
            method: 'class_weight' or 'smote'

        Returns:
            (X_train, y_train, class_weights)
        """
        logger.info(f"Handling class imbalance using: {method}")

        class_weights = None

        if method == 'class_weight':
            # Compute class weights
            classes = np.unique(y_train)
            weights = compute_class_weight('balanced', classes=classes, y=y_train)
            class_weights = dict(zip(classes, weights))
            logger.info(f"Class weights: {class_weights}")

        elif method == 'smote':
            # Apply SMOTE
            smote = SMOTE(random_state=42)
            X_train, y_train = smote.fit_resample(X_train, y_train)
            logger.info(f"After SMOTE: {len(y_train)} samples")

        return X_train, y_train, class_weights

    def train_model(self, X_train, y_train, model_type='random_forest',
                    class_weights=None, hyperparams=None):
        """
        Train a classification model

        Args:
            X_train: Training features
            y_train: Training labels
            model_type: Type of model to train
            class_weights: Class weights for imbalanced data
            hyperparams: Hyperparameters dictionary

        Returns:
            Trained model
        """
        logger.info(f"Training {model_type} model")

        if hyperparams is None:
            hyperparams = {}

        if model_type == 'logistic_regression':
            model = LogisticRegression(
                class_weight=class_weights or 'balanced',
                random_state=42,
                max_iter=1000,
                **hyperparams
            )

        elif model_type == 'decision_tree':
            model = DecisionTreeClassifier(
                class_weight=class_weights,
                random_state=42,
                **hyperparams
            )

        elif model_type == 'random_forest':
            model = RandomForestClassifier(
                class_weight=class_weights,
                random_state=42,
                n_estimators=hyperparams.get('n_estimators', 100),
                max_depth=hyperparams.get('max_depth', None),
                min_samples_split=hyperparams.get('min_samples_split', 2),
                min_samples_leaf=hyperparams.get('min_samples_leaf', 1),
                **{k: v for k, v in hyperparams.items()
                   if k not in ['n_estimators', 'max_depth', 'min_samples_split', 'min_samples_leaf']}
            )

        elif model_type == 'xgboost':
            scale_pos_weight = None
            if class_weights:
                scale_pos_weight = class_weights[0] / class_weights[1]

            model = XGBClassifier(
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                n_estimators=hyperparams.get('n_estimators', 100),
                max_depth=hyperparams.get('max_depth', 6),
                learning_rate=hyperparams.get('learning_rate', 0.1),
                **{k: v for k, v in hyperparams.items()
                   if k not in ['n_estimators', 'max_depth', 'learning_rate']}
            )

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Train model
        model.fit(X_train, y_train)
        logger.info(f"{model_type} training completed")

        return model

    def evaluate_model(self, model, X, y, dataset_name='Test'):
        """
        Evaluate model and return metrics

        Args:
            model: Trained model
            X: Features
            y: True labels
            dataset_name: Name of the dataset

        Returns:
            Dictionary of metrics
        """
        logger.info(f"Evaluating model on {dataset_name} set")

        # Predictions
        y_pred = model.predict(X)
        y_proba = model.predict_proba(X)[:, 1]

        # Compute metrics
        evaluator = ModelEvaluator(y, y_pred, y_proba)
        metrics = evaluator.compute_metrics()

        logger.info(f"{dataset_name} Metrics:")
        for metric_name, value in metrics.items():
            logger.info(f"  {metric_name}: {value:.4f}")

        # Check if target is met
        if metrics['f1_score'] >= 0.85 and metrics['recall'] >= 0.85:
            logger.info("✓ TARGET MET: F1-Score and Recall >= 85%")
        else:
            logger.warning("✗ Target not met. Further optimization required.")

        return metrics, evaluator

    def run_experiment(self, model_type='random_forest', use_smote=False,
                      hyperparams=None, use_engineered=True):
        """
        Run complete model training experiment with MLflow tracking

        Args:
            model_type: Type of model to train
            use_smote: Whether to use SMOTE for class balancing
            hyperparams: Model hyperparameters
            use_engineered: Whether to use engineered features

        Returns:
            Trained model and test metrics
        """
        # Load and prepare data
        df = self.load_data()
        df, feature_cols, target_col = self.prepare_features(df, use_engineered=use_engineered)

        # Split data
        X_train, X_val, X_test, y_train, y_val, y_test, feature_cols = self.split_data(
            df, feature_cols, target_col
        )

        # Scale features
        X_train_scaled, X_val_scaled, X_test_scaled = self.scale_features(
            X_train, X_val, X_test
        )

        # Handle class imbalance
        imbalance_method = 'smote' if use_smote else 'class_weight'
        X_train_balanced, y_train_balanced, class_weights = self.handle_class_imbalance(
            X_train_scaled, y_train, method=imbalance_method
        )

        # Start MLflow run
        run_name = f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with self.mlflow_manager.start_run(run_name=run_name) as run:
            # Log parameters
            params = {
                'model_type': model_type,
                'imbalance_method': imbalance_method,
                'n_train_samples': len(y_train),
                'n_val_samples': len(y_val),
                'n_test_samples': len(y_test),
                'n_features': len(feature_cols),
                'class_imbalance_ratio': f"1:{len(y_train) / np.sum(y_train):.1f}"
            }

            if hyperparams:
                params.update(hyperparams)

            self.mlflow_manager.log_params(params)

            # Train model
            model = self.train_model(
                X_train_balanced, y_train_balanced,
                model_type=model_type,
                class_weights=class_weights,
                hyperparams=hyperparams
            )

            # Evaluate on validation set
            val_metrics, val_evaluator = self.evaluate_model(
                model, X_val_scaled, y_val, dataset_name='Validation'
            )

            # Evaluate on test set
            test_metrics, test_evaluator = self.evaluate_model(
                model, X_test_scaled, y_test, dataset_name='Test'
            )

            # Log metrics
            for metric_name, value in val_metrics.items():
                self.mlflow_manager.log_metrics({f'val_{metric_name}': value})

            for metric_name, value in test_metrics.items():
                self.mlflow_manager.log_metrics({f'test_{metric_name}': value})

            # Generate and log visualizations
            artifact_dir = Path('mlruns/artifacts') / run.info.run_id
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # Confusion matrix
            cm_path = artifact_dir / 'confusion_matrix.png'
            test_evaluator.generate_confusion_matrix(save_path=cm_path)
            self.mlflow_manager.log_artifact(cm_path)

            # ROC curve
            roc_path = artifact_dir / 'roc_curve.png'
            test_evaluator.generate_roc_curve(save_path=roc_path)
            self.mlflow_manager.log_artifact(roc_path)

            # PR curve
            pr_path = artifact_dir / 'precision_recall_curve.png'
            test_evaluator.generate_precision_recall_curve(save_path=pr_path)
            self.mlflow_manager.log_artifact(pr_path)

            # Log model
            self.mlflow_manager.log_model(
                model,
                artifact_path='model',
                input_example=X_train_scaled[:5]
            )

            logger.info(f"MLflow run completed: {run.info.run_id}")

        return model, test_metrics


def main():
    """Main training script"""
    parser = argparse.ArgumentParser(description='Train OLPA predictive maintenance model')

    parser.add_argument('--data_path', type=str, default='data/processed/gold_ml_dataset.csv',
                        help='Path to sensor data CSV')
    parser.add_argument('--model_type', type=str, default='random_forest',
                        choices=['logistic_regression', 'decision_tree', 'random_forest', 'xgboost'],
                        help='Type of model to train')
    parser.add_argument('--use_smote', action='store_true',
                        help='Use SMOTE for class balancing')
    parser.add_argument('--use_engineered', action='store_true', default=True,
                        help='Use engineered features')

    args = parser.parse_args()

    # Initialize predictor
    predictor = MaintenancePredictor(data_path=args.data_path)

    # Run experiment
    model, metrics = predictor.run_experiment(
        model_type=args.model_type,
        use_smote=args.use_smote,
        use_engineered=args.use_engineered
    )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETED")
    print("=" * 60)
    print(f"\nModel Type: {args.model_type}")
    print("\nTest Set Performance:")
    for metric_name, value in metrics.items():
        print(f"  {metric_name}: {value:.4f}")

    if metrics['f1_score'] >= 0.85 and metrics['recall'] >= 0.85:
        print("\n✓ SUCCESS: Target metrics achieved (F1 & Recall >= 85%)")
    else:
        print("\n✗ Target not met. Try hyperparameter tuning or feature engineering.")


if __name__ == "__main__":
    main()
