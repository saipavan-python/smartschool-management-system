DROP DATABASE IF EXISTS smartschool;
CREATE DATABASE smartschool;
USE smartschool;

-- USERS
CREATE TABLE users (
    user_id VARCHAR(30) PRIMARY KEY,
    password VARCHAR(50),
    role ENUM('admin','principal','teacher','student','parent')
);

-- STUDENTS
CREATE TABLE students (
    student_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100),
    class VARCHAR(10),
    parent_phone VARCHAR(15)
);

-- PARENTS
CREATE TABLE parents (
    parent_id VARCHAR(30) PRIMARY KEY,
    student_id VARCHAR(30),
    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
);

-- TEACHERS
CREATE TABLE teachers (
    teacher_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100),
    subject VARCHAR(50)
);

-- MARKS
CREATE TABLE marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(30),
    subject VARCHAR(50),
    internal INT DEFAULT 0,
    mid INT DEFAULT 0,
    final INT DEFAULT 0,
    UNIQUE(student_id, subject),
    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
);

-- ATTENDANCE
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(30),
    date DATE,
    status ENUM('Present','Absent'),
    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
);

-- WEEKLY TESTS
CREATE TABLE weekly_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(30),
    subject VARCHAR(50),
    marks INT,
    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
        ON DELETE CASCADE
);

-- NOTES
CREATE TABLE notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(10),
    subject VARCHAR(50),
    chapter VARCHAR(100),
    file_name VARCHAR(255)
);

-- TIMETABLE
CREATE TABLE timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(10),
    day VARCHAR(20),
    time VARCHAR(50),
    subject VARCHAR(50)
);

-- ANNOUNCEMENTS
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(10),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HOLIDAYS
CREATE TABLE holidays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE,
    reason VARCHAR(255)
);

-- DEMO DATA
INSERT INTO users VALUES ('admin','admin','admin');
INSERT INTO users VALUES ('principal','principal','principal');

INSERT INTO teachers VALUES ('TCH101','Anita Sharma','Math');
INSERT INTO users VALUES ('TCH101','teacher','teacher');

INSERT INTO students VALUES ('STU1001','Aarav Kumar','6-A','900000001');
INSERT INTO users VALUES ('STU1001','student','student');

INSERT INTO parents VALUES ('PARSTU1001','STU1001');
INSERT INTO users VALUES ('PARSTU1001','parent','parent');