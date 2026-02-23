CREATE TABLE students ( 
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    grade FLOAT,
    attendance_rate FLOAT,
    cost FLOAT,
    risk_score INT,
    risk_label INT
   );

CREATE TABLE interventions (
    intervention_id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ALTER TABLE students
ADD CONSTRAINT unique_student_id UNIQUE (student_id);
