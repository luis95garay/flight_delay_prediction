from typing import Tuple, Union, List

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.utils import shuffle

from ..utils import get_min_diff, top_10_features


class DelayModel:

    def __init__(
        self
    ):
        self._model = None # Model should be saved in this attribute.
        self._feature_columns = None  # Store feature column names for consistency

    def preprocess(
        self,
        data: pd.DataFrame,
        target_column: str = None
    ) -> Union[Tuple[pd.DataFrame, pd.DataFrame], pd.DataFrame]:
        """
        Prepare raw data for training or predict.

        Args:
            data (pd.DataFrame): raw data.
            target_column (str, optional): if set, the target is returned.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: features and target.
            or
            pd.DataFrame: features.
        """
        data = data.copy()

        if target_column is not None:
            data['min_diff'] = data.apply(get_min_diff, axis=1)
            data[target_column] = np.where(data['min_diff'] > 15, 1, 0)
            data = shuffle(data[['OPERA', 'MES', 'TIPOVUELO', 'SIGLADES', 'DIANOM', 'delay']], random_state = 111)

        # Encode categorical features efficiently and handle missing values gracefully
        opera_dummies = pd.get_dummies(data['OPERA'], prefix='OPERA', dummy_na=True)
        tipovuelo_dummies = pd.get_dummies(data['TIPOVUELO'], prefix='TIPOVUELO', dummy_na=True)
        mes_dummies = pd.get_dummies(data['MES'], prefix='MES')

        features = pd.concat(
            [opera_dummies, tipovuelo_dummies, mes_dummies],
            axis=1
        )

        # Ensure consistent feature columns between training and prediction
        if self._feature_columns is None:
            # During training, store the feature column names
            self._feature_columns = features.columns.tolist()
        
        # For prediction, ensure all expected columns exist
        if self._feature_columns is not None:
            # Add missing columns with 0 values
            for col in self._feature_columns:
                if col not in features.columns:
                    features[col] = 0
            
            # Remove extra columns that weren't in training
            features = features[self._feature_columns]

        # Filter to top 10 features
        features = features[top_10_features]

        if target_column is not None:
            target = data[[target_column]]
            return features, target
        return features

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.DataFrame
    ) -> None:
        """
        Fit model with preprocessed data.

        Args:
            features (pd.DataFrame): preprocessed data.
            target (pd.DataFrame): target.
        """
        target = target.delay

        n_y0 = len(target[target == 0])
        n_y1 = len(target[target == 1])
        scale = n_y0/n_y1

        xgb_model = xgb.XGBClassifier(random_state=1, learning_rate=0.01, scale_pos_weight = scale)
        xgb_model.fit(features, target)
        self._model = xgb_model

    def predict(
        self,
        features: pd.DataFrame
    ) -> List[int]:
        """
        Predict delays for new flights.

        Args:
            features (pd.DataFrame): preprocessed data.
        
        Returns:
            (List[int]): predicted targets.
        """
        predictions = self._model.predict(features)
        return predictions.tolist()