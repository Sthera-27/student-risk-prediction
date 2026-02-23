import
 os
import
 streamlit 
as
 st
import
 psycopg2
import
 psycopg2.extras
import
 pandas 
as
 pd
import
 requests
st.set_page_config(page_title=
"Student Risk Dashboard"
, layout=
"wide"
)
# Config from environment

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
)  
# e.g., "require" or None

BACKEND_URL = os.getenv(
"BACKEND_URL"
, 
"http://127.0.0.1:8000"
)
st.title(
"📊 Student Risk Dashboard"
)
def
 
get_db_connection
():

    conn_params = {
        
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
        conn_params[
"sslmode"
] = DB_SSLMODE
    
return
 psycopg2.connect(**conn_params)
@st.cache_data(
ttl=
30
)

def
 
load_students
():

    
try
:
        conn = get_db_connection()
        
# Use RealDictCursor so pandas can read easily, but read_sql works directly with connection

        df = pd.read_sql(
"SELECT * FROM students ORDER BY student_id"
, conn)
        conn.close()
        
return
 df
    
except
 Exception 
as
 e:
        st.error(
f"Failed to load students from DB: 
{e}
"
)
        
return
 pd.DataFrame()
students = load_students()
if
 students.empty:
    st.warning(
"No student data available."
)
else
:
    st.dataframe(students)
    student_id = st.selectbox(
"Select Student ID for Intervention"
, students[
"student_id"
].unique())
    
if
 st.button(
"Generate Intervention"
):
        
try
:
            url = 
f"
{BACKEND_URL.rstrip(
'/'
)}
/intervention/
{student_id}
"

            resp = requests.post(url, timeout=
10
)
            
if
 resp.ok:
                data = resp.json()
                rec = data.get(
"recommendation"
) 
or
 data.get(
"detail"
) 
or
 
str
(data)
                st.success(
f"Intervention: 
{rec}
"
)
            
else
:
                
# Try to show server's error message

                
try
:
                    err = resp.json()
                
except
 Exception:
                    err = resp.text
                st.error(
f"Failed to fetch intervention (status 
{resp.status_code}
): 
{err}
"
)
        
except
 requests.exceptions.RequestException 
as
 e:
            st.error(
f"Request failed: 
{e}
"
)
