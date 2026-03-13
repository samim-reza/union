CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name TEXT,
    age INT
);

INSERT INTO students (name, age)
VALUES ('Samim', 23);

SELECT * FROM students;