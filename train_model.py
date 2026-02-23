import
 os
import
 sys
import
 json
import
 pandas 
as
 pd
import
 numpy 
as
 np
from
 sklearn.preprocessing 
import
 MinMaxScaler
from
 sklearn.linear_model 
import
 LogisticRegression
from
 sklearn.model_selection 
import
 train_test_split
from
 sklearn.metrics 
import
 accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import
 joblib
# --- Config ---

GRADES_CSV = 
"student_grades.csv"

ATTENDANCE_CSV = 
"student_attendance.csv"

COSTS_CSV = 
"student_costs.csv"

MODEL_OUT = 
"student_risk_model.pkl"

SCALER_OUT = 
"scaler.pkl"

META_OUT = 
"model_metadata.json"

TEST_SIZE = 
0.2

RANDOM_STATE = 
42

# --- Helper: load CSV with checks ---

def
 
load_csv
(
path, required_columns
):

    
if
 
not
 os.path.exists(path):
        
raise
 FileNotFoundError(
f"Required file not found: 
{path}
"
)
    df = pd.read_csv(path)
    missing = [c 
for
 c 
in
 required_columns 
if
 c 
not
 
in
 df.columns]
    
if
 missing:
        
raise
 ValueError(
f"File 
{path}
 is missing required columns: 
{missing}
"
)
    
return
 df
# Load files with column expectations

grades_df = load_csv(GRADES_CSV, [
"student_id"
, 
"grade"
])
attendance_df = load_csv(ATTENDANCE_CSV, [
"student_id"
, 
"attended_classes"
, 
"total_classes"
])
cost_df = load_csv(COSTS_CSV, [
"student_id"
, 
"cost"
])
# Ensure numeric types and handle bad values

attendance_df[
"attended_classes"
] = pd.to_numeric(attendance_df[
"attended_classes"
], errors=
"coerce"
)
attendance_df[
"total_classes"
] = pd.to_numeric(attendance_df[
"total_classes"
], errors=
"coerce"
)
grades_df[
"grade"
] = pd.to_numeric(grades_df[
"grade"
], errors=
"coerce"
)
cost_df[
"cost"
] = pd.to_numeric(cost_df[
"cost"
], errors=
"coerce"
)
# Avoid division by zero — set attendance_rate to 0 if total_classes <= 0 or missing

attendance_df[
"attendance_rate"
] = np.where(
    (attendance_df[
"total_classes"
] > 
0
),
    attendance_df[
"attended_classes"
] / attendance_df[
"total_classes"
],
    
0.0

)
# Merge: inner join by default drops students missing in any file.

# If you want to keep all students and fill missing values, change how= is set and handle NaNs.

merged_df = grades_df.merge(attendance_df[[
"student_id"
, 
"attendance_rate"
]], on=
"student_id"
, how=
"inner"
) \
                     .merge(cost_df, on=
"student_id"
, how=
"inner"
)
# Optional: if you prefer to keep all students:

# merged_df = grades_df.merge(attendance_df[["student_id","attendance_rate"]], on="student_id", how="left") \

#                      .merge(cost_df, on="student_id", how="left")

# merged_df["attendance_rate"] = merged_df["attendance_rate"].fillna(0)

# merged_df["cost"] = merged_df["cost"].fillna(merged_df["cost"].median())

# Create flags — ensure no NaNs

merged_df[
"attendance_rate"
] = merged_df[
"attendance_rate"
].fillna(
0
)
merged_df[
"grade"
] = merged_df[
"grade"
].fillna(
0
)
merged_df[
"cost"
] = merged_df[
"cost"
].fillna(merged_df[
"cost"
].median())
merged_df[
"low_attendance_flag"
] = (merged_df[
"attendance_rate"
] < 
0.75
).astype(
int
)
merged_df[
"low_grade_flag"
] = (merged_df[
"grade"
] < 
50
).astype(
int
)
merged_df[
"high_cost_burden"
] = (merged_df[
"cost"
] > merged_df[
"cost"
].median()).astype(
int
)
merged_df[
"risk_score"
] = merged_df[
"low_attendance_flag"
] + merged_df[
"low_grade_flag"
] + merged_df[
"high_cost_burden"
]
merged_df[
"risk_label"
] = (merged_df[
"risk_score"
] >= 
2
).astype(
int
)
# Features and label

FEATURE_COLS = [
"attendance_rate"
, 
"grade"
, 
"cost"
, 
"low_attendance_flag"
, 
"low_grade_flag"
, 
"high_cost_burden"
]
X = merged_df[FEATURE_COLS].values
y = merged_df[
"risk_label"
].values
# Scale

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
# Train/test split

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y 
if
 
len
(np.unique(y))>
1
 
else
 
None
)
# Train model

model = LogisticRegression(solver=
"lbfgs"
, max_iter=
1000
, random_state=RANDOM_STATE)
model.fit(X_train, y_train)
# Evaluate

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 
1
] 
if
 
hasattr
(model, 
"predict_proba"
) 
else
 
None

metrics = {
    
"accuracy"
: 
float
(accuracy_score(y_test, y_pred)),
    
"precision"
: 
float
(precision_score(y_test, y_pred, zero_division=
0
)),
    
"recall"
: 
float
(recall_score(y_test, y_pred, zero_division=
0
)),
    
"f1"
: 
float
(f1_score(y_test, y_pred, zero_division=
0
)),
}
if
 y_proba 
is
 
not
 
None
 
and
 
len
(np.unique(y_test)) == 
2
:
    
try
:
        metrics[
"roc_auc"
] = 
float
(roc_auc_score(y_test, y_proba))
    
except
 Exception:
        metrics[
"roc_auc"
] = 
None

print
(
"Model metrics:"
, metrics)
print
(
"Confusion matrix:\n"
, confusion_matrix(y_test, y_pred))
# Save artifacts: model, scaler, and metadata (feature order)

joblib.dump(model, MODEL_OUT)
joblib.dump(scaler, SCALER_OUT)
metadata = {
    
"feature_columns"
: FEATURE_COLS,
    
"scaler"
: SCALER_OUT,
    
"model"
: MODEL_OUT,
    
"metrics"
: metrics
}
with
 
open
(META_OUT, 
"w"
) 
as
 f:
    json.dump(metadata, f, indent=
2
)
print
(
f"✅ Model saved to 
{MODEL_OUT}
, scaler to 
{SCALER_OUT}
, metadata to 
{META_OUT}
"
)
