import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

df = pd.read_csv("EV_Charging_Ahmedabad_Gandhinagar_1000_highscores.csv")

X = df.drop(columns=["score"])
y = df["score"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    min_samples_leaf=5,
    random_state=42
)

model.fit(X_train, y_train)

pred = model.predict(X_test)

r2   = r2_score(y_test, pred)
mae  = mean_absolute_error(y_test, pred)
rmse = np.sqrt(mean_squared_error(y_test, pred))

print("R2 Score:", r2)
print("MAE:", mae)
print("RMSE:", rmse)

joblib.dump(model, "ev_site_model.pkl")
print("Model saved as ev_site_model.pkl")