import
 os
import
 logging
from
 fastapi 
import
 FastAPI, HTTPException
from
 pydantic 
import
 BaseModel, Field, conint, confloat
import
 pandas 
as
 pd
import
 joblib
import
 numpy 
as
 np
import
 psycopg2
from
 psycopg2 
import
 sql
from
 psycopg2.pool 
import
 ThreadedConnectionPool
from
 typing 
import
 
Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
# Environment / DB config

DB_NAME = os.getenv(
"DB_NAME"
, 
"postgres"
)
DB_USER = os.getenv(
"DB_USER"
, 
"postgres"
)
DB_PASSWORD = os.getenv(
"DB_PASSWORD"
, 
""
)
DB_HOST = os.getenv(
"DB_HOST"
, 
"localhost"
)
DB_PORT = os.getenv(
"DB_PORT"
, 
"5432"
)
DB_SSLMODE = os.getenv(
"DB_SSLMODE"
, 
None
)  
# set to 'require' if needed

DB_MIN_CONN = 
int
(os.getenv(
"DB_MIN_CONN"
, 
"1"
))
DB_MAX_CONN = 
int
(os.getenv(
"DB_MAX_CONN"
, 
"10"
))
pool: 
Optional
[ThreadedConnectionPool] = 
None

# Load model and scaler once (with basic error handling)

MODEL_PATH = os.getenv(
"MODEL_PATH"
, 
"student_risk_model.pkl"
)
SCALER_PATH = os.getenv(
"SCALER_PATH"
, 
"scaler.pkl"
)
try
:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    logger.info(
"Model and scaler loaded successfully."
)
except
 Exception 
as
 e:
    logger.exception(
"Failed to load model or scaler."
)
    
raise

class
 
StudentData
(
BaseModel
):

    student_id: 
int
 = Field(..., ge=
1
)
    grade: confloat(ge=
0
, le=
100
)
    attendance_rate: confloat(ge=
0
, le=
1
)
    cost: 
float
 = Field(..., ge=
0
)
    low_attendance_flag: conint(ge=
0
, le=
1
)
    low_grade_flag: conint(ge=
0
, le=
1
)
    high_cost_burden: conint(ge=
0
, le=
1
)
def
 
get_db_dsn
():

    
# Build DSN dict and include sslmode only if set

    dsn = {
        
"dbname"
: DB_NAME,
        
"user"
: DB_USER,
        
"password"
: DB_PASSWORD,
        
"host"
: DB_HOST,
        
"port"
: DB_PORT,
    }
    
if
 DB_SSLMODE:
        dsn[
"sslmode"
] = DB_SSLMODE
    
return
 dsn
@app.on_event(
"startup"
)

def
 
startup
():

    
global
 pool
    dsn = get_db_dsn()
    
try
:
        pool = ThreadedConnectionPool(minconn=DB_MIN_CONN, maxconn=DB_MAX_CONN, **dsn)
        logger.info(
"Database connection pool created."
)
    
except
 Exception 
as
 e:
        logger.exception(
"Failed to create DB connection pool."
)
        
raise

@app.on_event(
"shutdown"
)

def
 
shutdown
():

    
global
 pool
    
if
 pool:
        pool.closeall()
        logger.info(
"Database connection pool closed."
)
def
 
to_native
(
val
):

    
# Convert numpy types to native Python types

    
if
 
isinstance
(val, (np.generic,)):
        
return
 val.item()
    
return
 val
@app.post(
"/predict"
)

def
 
predict
(
student: StudentData
):

    
global
 pool, model, scaler
    
if
 pool 
is
 
None
:
        
raise
 HTTPException(status_code=
500
, detail=
"DB pool not initialized."
)
    features = [
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
    
try
:
        df = pd.DataFrame([student.
dict
()])
        
# Ensure columns exist

        
for
 f 
in
 features:
            
if
 f 
not
 
in
 df.columns:
                
raise
 HTTPException(status_code=
400
, detail=
f"Missing feature: 
{f}
"
)
        scaled = scaler.transform(df[features])
        prediction_np = model.predict(scaled)[
0
]
        prob_np = model.predict_proba(scaled)[
0
][
1
] 
if
 
hasattr
(model, 
"predict_proba"
) 
else
 
None

        prediction = 
int
(to_native(prediction_np))
        prob = 
float
(to_native(prob_np)) 
if
 prob_np 
is
 
not
 
None
 
else
 
None

        risk_score = 
int
(student.low_attendance_flag + student.low_grade_flag + student.high_cost_burden)
        conn = pool.getconn()
        
try
:
            
with
 conn.cursor() 
as
 cur:
                insert_query = 
"""
                    INSERT INTO students (student_id, grade, attendance_rate, cost, risk_score, risk_label)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (student_id) DO UPDATE SET
                        grade = EXCLUDED.grade,
                        attendance_rate = EXCLUDED.attendance_rate,
                        cost = EXCLUDED.cost,
                        risk_score = EXCLUDED.risk_score,
                        risk_label = EXCLUDED.risk_label;
                """

                cur.execute(
                    insert_query,
                    (
                        student.student_id,
                        student.grade,
                        student.attendance_rate,
                        student.cost,
                        risk_score,
                        prediction,
                    ),
                )
            conn.commit()
        
except
 Exception 
as
 e:
            conn.rollback()
            logger.exception(
"DB write failed."
)
            
raise
 HTTPException(status_code=
500
, detail=
f"DB write failed: 
{
str
(e)}
"
)
        
finally
:
            pool.putconn(conn)
        result = {
"risk_label"
: prediction}
        
if
 prob 
is
 
not
 
None
:
            result[
"risk_probability"
] = prob
        
return
 result
    
except
 HTTPException:
        
raise

    
except
 Exception 
as
 e:
        logger.exception(
"Prediction failed."
)
        
raise
 HTTPException(status_code=
500
, detail=
f"Prediction failed: 
{
str
(e)}
"
)
@app.post(
"/intervention/{student_id}"
)

def
 
intervention
(
student_id: 
int
):

    
global
 pool
    
if
 pool 
is
 
None
:
        
raise
 HTTPException(status_code=
500
, detail=
"DB pool not initialized."
)
    conn = pool.getconn()
    
try
:
        
with
 conn.cursor() 
as
 cur:
            cur.execute(
"SELECT risk_label FROM students WHERE student_id = %s"
, (student_id,))
            row = cur.fetchone()
            
if
 
not
 row:
                
raise
 HTTPException(status_code=
404
, detail=
"Student not found."
)
            risk_label = row[
0
]
            
if
 risk_label == 
1
:
                rec = 
"Provide tutoring support, financial aid counseling, and attendance monitoring."

            
else
:
                rec = 
"Encourage continued engagement and reward consistent performance."

            cur.execute(
                
"""
                INSERT INTO interventions (student_id, recommendation)
                VALUES (%s, %s)
                """
,
                (student_id, rec),
            )
        conn.commit()
        
return
 {
"student_id"
: student_id, 
"recommendation"
: rec}
    
except
 HTTPException:
        
raise

    
except
 Exception 
as
 e:
        conn.rollback()
        logger.exception(
"Intervention failed."
)
        
raise
 HTTPException(status_code=
500
, detail=
f"Intervention failed: 
{
str
(e)}
"
)
    
finally
:
        pool.putconn(conn)
