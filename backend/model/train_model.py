import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
import logging

logging.basicConfig(level=logging.INFO)

# Load data
data = pd.read_csv('../student_data.csv')
logging.info("Loaded data: %s", data.head())

# Separate features and target
X = data[['subject', 'progress']]
y = data['next_best_exercise']

# Encode categorical features and target
categorical_features = ['subject']
categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

# Encode the target variable
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Create a column transformer to apply one-hot encoding to categorical features
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', categorical_transformer, categorical_features)],
    remainder='passthrough'
)

# Create a pipeline that first transforms the data and then fits the model
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier())
])

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# Log the transformed training data
X_train_transformed = preprocessor.fit_transform(X_train)
logging.info("Transformed training data shape: %s", X_train_transformed.shape)
logging.info("Transformed training data: %s", X_train_transformed)

# Train the model
pipeline.fit(X_train, y_train)

# Save the entire pipeline, including the preprocessor
joblib.dump(pipeline, 'personalized_model.pkl')
joblib.dump(label_encoder, 'label_encoder.pkl')
