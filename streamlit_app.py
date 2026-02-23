import
 os
import
 streamlit 
as
 st
import
 pandas 
as
 pd
from
 supabase 
import
 create_client, Client
from
 datetime 
import
 datetime
import
 io
import
 plotly.express 
as
 px
# -------------------------

# Configuration / Client

# -------------------------

SUPABASE_URL = os.getenv(
"SUPABASE_URL"
, 
"<SUPABASE_URL>"
)
SUPABASE_KEY = os.getenv(
"SUPABASE_SERVICE_ROLE_KEY"
, 
"<SUPABASE_SERVICE_ROLE_KEY>"
)
if
 
not
 SUPABASE_URL 
or
 
not
 SUPABASE_KEY 
or
 SUPABASE_URL.startswith(
"<"
):
    st.error(
"Supabase credentials not set. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
)
    st.stop()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# -------------------------

# Utility functions

# -------------------------

def
 
compute_risk_label
(
risk_score: 
int
) -> 
int
:

    
"""Default thresholds: <=3 low(0), 4-6 medium(1), >=7 high(2)."""

    
if
 risk_score 
is
 
None
:
        
return
 
None

    
try
:
        r = 
int
(risk_score)
    
except
 Exception:
        
return
 
None

    
if
 r <= 
3
:
        
return
 
0

    
if
 
4
 <= r <= 
6
:
        
return
 
1

    
return
 
2

def
 
fetch_students
():

    res = supabase.table(
"students"
).select(
"*"
).order(
"student_id"
, asc=
True
).execute()
    
if
 res.error:
        st.error(
f"Error fetching students: 
{res.error.message}
"
)
        
return
 pd.DataFrame()
    
return
 pd.DataFrame(res.data)
def
 
fetch_interventions
():

    res = supabase.table(
"interventions"
).select(
"*"
).order(
"created_at"
, asc=
False
).execute()
    
if
 res.error:
        st.error(
f"Error fetching interventions: 
{res.error.message}
"
)
        
return
 pd.DataFrame()
    
return
 pd.DataFrame(res.data)
def
 
add_student
(
name, grade, attendance_rate, cost, risk_score
):

    risk_label = compute_risk_label(risk_score)
    payload = {
        
"name"
: name,
        
"grade"
: grade,
        
"attendance_rate"
: attendance_rate,
        
"cost"
: cost,
        
"risk_score"
: risk_score,
        
"risk_label"
: risk_label,
    }
    res = supabase.table(
"students"
).insert(payload).execute()
    
if
 res.error:
        st.error(
f"Insert student error: 
{res.error.message}
"
)
        
return
 
False

    
return
 
True

def
 
update_student
(
student_id, **fields
):

    
# ensure risk_label computed if risk_score provided

    
if
 
"risk_score"
 
in
 fields:
        fields[
"risk_label"
] = compute_risk_label(fields[
"risk_score"
])
    res = supabase.table(
"students"
).update(fields).eq(
"student_id"
, student_id).execute()
    
if
 res.error:
        st.error(
f"Update error: 
{res.error.message}
"
)
        
return
 
False

    
return
 
True

def
 
add_intervention
(
student_id, recommendation
):

    payload = {
        
"student_id"
: student_id,
        
"recommendation"
: recommendation,
        
"created_at"
: datetime.utcnow().isoformat()
    }
    res = supabase.table(
"interventions"
).insert(payload).execute()
    
if
 res.error:
        st.error(
f"Insert intervention error: 
{res.error.message}
"
)
        
return
 
False

    
return
 
True

def
 
export_csv
(
df: pd.DataFrame, filename=
"export.csv"
):

    buf = io.StringIO()
    df.to_csv(buf, index=
False
)
    st.download_button(
"Download CSV"
, data=buf.getvalue(), file_name=filename, mime=
"text/csv"
)
# -------------------------

# UI

# -------------------------

st.set_page_config(page_title=
"Students Admin"
, layout=
"wide"
)
st.title(
"Students & Interventions Admin"
)
menu = st.sidebar.selectbox(
"Page"
, [
"Dashboard"
, 
"Students"
, 
"Interventions"
, 
"Export CSV"
])
if
 menu == 
"Dashboard"
:
    st.header(
"Dashboard"
)
    students_df = fetch_students()
    interventions_df = fetch_interventions()
    
if
 students_df.empty:
        st.info(
"No students found."
)
    
else
:
        col1, col2 = st.columns(
2
)
        
with
 col1:
            st.metric(
"Total students"
, 
len
(students_df))
            avg_grade = students_df[
"grade"
].dropna().astype(
float
).mean()
            st.metric(
"Average grade"
, 
f"
{avg_grade:
.2
f}
"
 
if
 
not
 pd.isna(avg_grade) 
else
 
"N/A"
)
        
with
 col2:
            avg_att = students_df[
"attendance_rate"
].dropna().astype(
float
).mean()
            st.metric(
"Average attendance"
, 
f"
{avg_att:
.2
f}
"
 
if
 
not
 pd.isna(avg_att) 
else
 
"N/A"
)
            st.metric(
"Total interventions"
, 
len
(interventions_df))
        
# Grade distribution

        fig_grade = px.histogram(students_df, x=
"grade"
, nbins=
20
, title=
"Grade distribution"
)
        st.plotly_chart(fig_grade, use_container_width=
True
)
        
# Attendance vs risk scatter

        
if
 
"attendance_rate"
 
in
 students_df.columns 
and
 
"risk_score"
 
in
 students_df.columns:
            fig_scatter = px.scatter(students_df, x=
"attendance_rate"
, y=
"risk_score"
, color=students_df.get(
"risk_label"
),
                                     labels={
"color"
: 
"risk_label"
}, title=
"Attendance vs Risk Score"
)
            st.plotly_chart(fig_scatter, use_container_width=
True
)
        
# Risk label counts

        
if
 
"risk_label"
 
in
 students_df.columns:
            rl_counts = students_df[
"risk_label"
].value_counts().sort_index()
            rl_df = rl_counts.reset_index()
            rl_df.columns = [
"risk_label"
, 
"count"
]
            fig_rl = px.bar(rl_df, x=
"risk_label"
, y=
"count"
, title=
"Risk label counts"
)
            st.plotly_chart(fig_rl, use_container_width=
True
)
if
 menu == 
"Students"
:
    st.header(
"Students"
)
    students_df = fetch_students()
    st.subheader(
"Add new student"
)
    
with
 st.form(
"add_student"
):
        name = st.text_input(
"Name"
)
        grade = st.number_input(
"Grade"
, min_value=
0.0
, max_value=
100.0
, value=
0.0
, step=
0.1
)
        attendance_rate = st.number_input(
"Attendance rate (0-100)"
, min_value=
0.0
, max_value=
100.0
, value=
100.0
, step=
0.1
)
        cost = st.number_input(
"Cost"
, min_value=
0.0
, value=
0.0
, step=
0.01
, 
format
=
"%.2f"
)
        risk_score = st.number_input(
"Risk score (integer)"
, min_value=
0
, max_value=
100
, value=
0
, step=
1
)
        submitted = st.form_submit_button(
"Add student"
)
        
if
 submitted:
            ok = add_student(name, 
float
(grade), 
float
(attendance_rate), 
float
(cost), 
int
(risk_score))
            
if
 ok:
                st.success(
"Student added."
)
                students_df = fetch_students()
    st.subheader(
"Existing students"
)
    
if
 students_df.empty:
        st.info(
"No students yet."
)
    
else
:
        
# Search / filter

        cols = st.columns([
3
,
1
,
1
,
1
,
1
,
1
])
        
with
 cols[
0
]:
            q = st.text_input(
"Search by name"
)
        
with
 cols[
1
]:
            fl_risk = st.selectbox(
"Risk label"
, options=[
"All"
, 
0
,
1
,
2
], index=
0
)
        df_view = students_df.copy()
        
if
 q:
            df_view = df_view[df_view[
"name"
].
str
.contains(q, case=
False
, na=
False
)]
        
if
 fl_risk != 
"All"
:
            df_view = df_view[df_view[
"risk_label"
] == fl_risk]
        st.data_editor(df_view, num_rows=
"dynamic"
, use_container_width=
True
, key=
"students_editor"
)
        st.markdown(
"### Edit student"
)
        
with
 st.form(
"edit_student"
):
            sid = st.number_input(
"Student ID"
, min_value=
1
, value=
1
, step=
1
)
            name_u = st.text_input(
"Name (leave blank to keep)"
)
            grade_u = st.text_input(
"Grade (leave blank to keep)"
)
            att_u = st.text_input(
"Attendance rate (leave blank to keep)"
)
            cost_u = st.text_input(
"Cost (leave blank to keep)"
)
            risk_score_u = st.text_input(
"Risk score (leave blank to keep)"
)
            upd = st.form_submit_button(
"Update student"
)
            
if
 upd:
                fields = {}
                
if
 name_u:
                    fields[
"name"
] = name_u
                
if
 grade_u:
                    fields[
"grade"
] = 
float
(grade_u)
                
if
 att_u:
                    fields[
"attendance_rate"
] = 
float
(att_u)
                
if
 cost_u:
                    fields[
"cost"
] = 
float
(cost_u)
                
if
 risk_score_u:
                    fields[
"risk_score"
] = 
int
(risk_score_u)
                
if
 
not
 fields:
                    st.info(
"No fields to update."
)
                
else
:
                    ok = update_student(
int
(sid), **fields)
                    
if
 ok:
                        st.success(
"Student updated."
)
                        students_df = fetch_students()
if
 menu == 
"Interventions"
:
    st.header(
"Interventions"
)
    interventions_df = fetch_interventions()
    students_df = fetch_students()
    st.subheader(
"Add intervention"
)
    
with
 st.form(
"add_interv"
):
        
if
 students_df.empty:
            st.info(
"No students available to add interventions."
)
        
else
:
            sid = st.selectbox(
"Student"
, options=students_df[
"student_id"
].tolist(),
                               format_func=
lambda
 x: 
f"
{x}
 - 
{students_df.loc[students_df[
'student_id'
]==x, 
'name'
].values[
0
]}
"
)
            recommendation = st.text_area(
"Recommendation"
)
            sub = st.form_submit_button(
"Add intervention"
)
            
if
 sub:
                ok = add_intervention(
int
(sid), recommendation)
                
if
 ok:
                    st.success(
"Intervention added."
)
                    interventions_df = fetch_interventions()
    st.subheader(
"Recent interventions"
)
    
if
 interventions_df.empty:
        st.info(
"No interventions yet."
)
    
else
:
        
# join student names if available

        
if
 
not
 students_df.empty:
            merged = interventions_df.merge(students_df[[
"student_id"
, 
"name"
]], how=
"left"
, left_on=
"student_id"
, right_on=
"student_id"
)
        
else
:
            merged = interventions_df.copy()
        st.dataframe(merged, use_container_width=
True
)
if
 menu == 
"Export CSV"
:
    st.header(
"Export data"
)
    students_df = fetch_students()
    interventions_df = fetch_interventions()
    
if
 
not
 students_df.empty:
        st.subheader(
"Students CSV"
)
        export_csv(students_df, filename=
"students_export.csv"
)
    
else
:
        st.info(
"No students to export."
)
    
if
 
not
 interventions_df.empty:
        st.subheader(
"Interventions CSV"
)
        export_csv(interventions_df, filename=
"interventions_export.csv"
)
