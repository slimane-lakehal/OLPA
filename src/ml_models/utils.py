"""
ML Utilities for OLPA Project
MLflow integration, model evaluation, and time-series handling
"""

import mlflow
import mlflow.sklearn
# import mlflow.tensorflow  # Optional - only needed for TensorFlow models
from mlflow.models.signature import infer_signature
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    f1_score, recall_score, precision_score, accuracy_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report, roc_curve, precision_recall_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLflowManager:
    """
    Manages MLflow experiment tracking and model logging
    """

    def __init__(self, config_path='config/mlflow_config.yaml'):
        """
        Initialize MLflow with configuration

        Args:
            config_path: Path to MLflow configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._setup_mlflow()

    def _load_config(self):
        """Load MLflow configuration from YAML"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
            return self._default_config()

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _default_config(self):
        """Default configuration if file doesn't exist"""
        return {
            'mlflow': {
                'tracking': {
                    'backend_uri': 'sqlite:///mlruns/mlflow.db',
                    'artifact_location': 'mlruns/artifacts',
                    'default_experiment_name': 'olpa_predictive_maintenance'
                },
                'autolog': {
                    'sklearn': True,
                    'tensorflow': True,
                    'log_models': True
                }
            }
        }

    def _setup_mlflow(self):
        """Configure MLflow tracking"""
        tracking_config = self.config['mlflow']['tracking']

        # Set tracking URI
        mlflow.set_tracking_uri(tracking_config['backend_uri'])

        # Set default experiment
        experiment_name = tracking_config['default_experiment_name']

        # Create experiment if it doesn't exist
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            mlflow.create_experiment(
                experiment_name,
                artifact_location=tracking_config.get('artifact_location')
            )

        mlflow.set_experiment(experiment_name)

        # Enable autologging if configured
        autolog_config = self.config['mlflow'].get('autolog', {})
        if autolog_config.get('sklearn', False):
            mlflow.sklearn.autolog(log_models=autolog_config.get('log_models', True))
        # TensorFlow autologging disabled (TF not installed)
        # if autolog_config.get('tensorflow', False):
        #     mlflow.tensorflow.autolog(log_models=autolog_config.get('log_models', True))

        logger.info(f"MLflow configured: {tracking_config['backend_uri']}")
        logger.info(f"Active experiment: {experiment_name}")

    def start_run(self, run_name=None, tags=None, nested=False):
        """
        Start a new MLflow run

        Args:
            run_name: Name for the run
            tags: Dictionary of tags
            nested: Whether this is a nested run

        Returns:
            MLflow run context manager
        """
        default_tags = self.config['mlflow'].get('run', {}).get('tags', {})
        if tags:
            default_tags.update(tags)

        return mlflow.start_run(run_name=run_name, tags=default_tags, nested=nested)

    def log_metrics(self, metrics_dict, step=None):
        """
        Log metrics to MLflow

        Args:
            metrics_dict: Dictionary of metric name -> value
            step: Optional step number
        """
        for metric_name, value in metrics_dict.items():
            mlflow.log_metric(metric_name, value, step=step)

    def log_params(self, params_dict):
        """
        Log parameters to MLflow

        Args:
            params_dict: Dictionary of parameter name -> value
        """
        mlflow.log_params(params_dict)

    def log_model(self, model, artifact_path, signature=None, input_example=None):
        """
        Log a model to MLflow

        Args:
            model: Model object
            artifact_path: Path within the artifact storage
            signature: Model signature
            input_example: Example input for the model
        """
        # Auto-detect model type
        model_type = type(model).__module__

        if 'sklearn' in model_type:
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                signature=signature,
                input_example=input_example
            )
        # elif 'tensorflow' in model_type or 'keras' in model_type:
        #     mlflow.tensorflow.log_model(
        #         model,
        #         artifact_path,
        #         signature=signature,
        #         input_example=input_example
        #     )
        else:
            # Generic sklearn model (most common case)
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                signature=signature,
                input_example=input_example
            )

        logger.info(f"Model logged to: {artifact_path}")

    def log_artifact(self, local_path, artifact_path=None):
        """
        Log an artifact (file) to MLflow

        Args:
            local_path: Path to local file
            artifact_path: Path within artifact storage
        """
        mlflow.log_artifact(local_path, artifact_path)

    def register_model(self, model_uri, model_name):
        """
        Register a model in MLflow Model Registry

        Args:
            model_uri: URI of the model
            model_name: Name for the registered model

        Returns:
            ModelVersion object
        """
        model_version = mlflow.register_model(model_uri, model_name)
        logger.info(f"Model registered: {model_name} version {model_version.version}")
        return model_version


class ModelEvaluator:
    """
    Evaluate classification models with comprehensive metrics
    """

    def __init__(self, y_true, y_pred, y_proba=None):
        """
        Initialize evaluator

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities (optional)
        """
        self.y_true = y_true
        self.y_pred = y_pred
        self.y_proba = y_proba

    def compute_metrics(self):
        """
        Compute all evaluation metrics

        Returns:
            Dictionary of metrics
        """
        metrics = {
            'f1_score': f1_score(self.y_true, self.y_pred),
            'recall': recall_score(self.y_true, self.y_pred),
            'precision': precision_score(self.y_true, self.y_pred),
            'accuracy': accuracy_score(self.y_true, self.y_pred)
        }

        # Add probability-based metrics if available
        if self.y_proba is not None:
            metrics['roc_auc'] = roc_auc_score(self.y_true, self.y_proba)
            metrics['average_precision'] = average_precision_score(self.y_true, self.y_proba)

        return metrics

    def generate_confusion_matrix(self, save_path=None):
        """
        Generate and optionally save confusion matrix plot

        Args:
            save_path: Path to save the plot

        Returns:
            Confusion matrix array
        """
        cm = confusion_matrix(self.y_true, self.y_pred)

        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
        plt.title('Confusion Matrix', fontsize=16, fontweight='bold')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Confusion matrix saved to {save_path}")

        return cm

    def generate_roc_curve(self, save_path=None):
        """
        Generate and optionally save ROC curve plot

        Args:
            save_path: Path to save the plot

        Returns:
            (fpr, tpr, thresholds)
        """
        if self.y_proba is None:
            logger.warning("Cannot generate ROC curve without probability predictions")
            return None

        fpr, tpr, thresholds = roc_curve(self.y_true, self.y_proba)
        auc = roc_auc_score(self.y_true, self.y_proba)

        plt.figure(figsize=(10, 8))
        plt.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (AUC = {auc:.3f})')
        plt.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--', label='Random')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title('Receiver Operating Characteristic (ROC) Curve', fontsize=16, fontweight='bold')
        plt.legend(loc="lower right")
        plt.grid(alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"ROC curve saved to {save_path}")

        return fpr, tpr, thresholds

    def generate_precision_recall_curve(self, save_path=None):
        """
        Generate and optionally save precision-recall curve

        Args:
            save_path: Path to save the plot

        Returns:
            (precision, recall, thresholds)
        """
        if self.y_proba is None:
            logger.warning("Cannot generate PR curve without probability predictions")
            return None

        precision, recall, thresholds = precision_recall_curve(self.y_true, self.y_proba)
        avg_precision = average_precision_score(self.y_true, self.y_proba)

        plt.figure(figsize=(10, 8))
        plt.plot(recall, precision, color='green', lw=2, label=f'PR curve (AP = {avg_precision:.3f})')
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title('Precision-Recall Curve', fontsize=16, fontweight='bold')
        plt.legend(loc="lower left")
        plt.grid(alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"PR curve saved to {save_path}")

        return precision, recall, thresholds

    def print_classification_report(self):
        """Print detailed classification report"""
        print("\nClassification Report:")
        print("=" * 60)
        print(classification_report(self.y_true, self.y_pred, target_names=['No Failure', 'Failure']))


class TimeSeriesSplit:
    """
    Time-series aware train/validation/test split
    Prevents data leakage in temporal data
    """

    def __init__(self, df, date_column='date', gap_days=7):
        """
        Initialize time-series splitter

        Args:
            df: DataFrame with temporal data
            date_column: Name of the date column
            gap_days: Gap between train and validation to prevent leakage
        """
        self.df = df.sort_values(date_column).reset_index(drop=True)
        self.date_column = date_column
        self.gap_days = gap_days

    def split(self, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
        """
        Split data into train/validation/test sets

        Args:
            train_ratio: Proportion for training
            val_ratio: Proportion for validation
            test_ratio: Proportion for testing

        Returns:
            (train_df, val_df, test_df)
        """
        assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 0.01, "Ratios must sum to 1"

        n = len(self.df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        # Apply gap between train and validation
        train_df = self.df.iloc[:train_end]
        val_start = train_end + self.gap_days
        val_df = self.df.iloc[val_start:val_end]
        test_start = val_end + self.gap_days
        test_df = self.df.iloc[test_start:]

        logger.info(f"Train set: {len(train_df)} samples ({train_df[self.date_column].min()} to {train_df[self.date_column].max()})")
        logger.info(f"Validation set: {len(val_df)} samples ({val_df[self.date_column].min()} to {val_df[self.date_column].max()})")
        logger.info(f"Test set: {len(test_df)} samples ({test_df[self.date_column].min()} to {test_df[self.date_column].max()})")
        logger.info(f"Gap between sets: {self.gap_days} days")

        return train_df, val_df, test_df

    def get_xy(self, df, feature_cols, target_col):
        """
        Extract features and target from DataFrame

        Args:
            df: DataFrame
            feature_cols: List of feature column names
            target_col: Target column name

        Returns:
            (X, y)
        """
        X = df[feature_cols].values
        y = df[target_col].values
        return X, y


if __name__ == "__main__":
    # Example usage
    print("ML Utilities Module for OLPA")
    print("=" * 60)

    # Initialize MLflow
    mlflow_manager = MLflowManager()
    print("MLflow initialized successfully")

    # Example time-series split
    print("\nExample: Time-Series Split")
    sample_df = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=100),
        'feature': np.random.randn(100),
        'target': np.random.randint(0, 2, 100)
    })

    splitter = TimeSeriesSplit(sample_df, date_column='date', gap_days=7)
    train, val, test = splitter.split(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
