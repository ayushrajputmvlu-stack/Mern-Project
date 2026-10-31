CREATE DATABASE IF NOT EXISTS community_health_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE community_health_db;

CREATE TABLE IF NOT EXISTS workers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'worker') NOT NULL DEFAULT 'worker',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS people (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(30) NULL,
    phone VARCHAR(20) NULL,
    address TEXT NULL,
    blood_group VARCHAR(5) NULL,
    allergies TEXT NULL,
    health_issues TEXT NULL,
    emergency_contact VARCHAR(20) NULL,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_people_worker FOREIGN KEY (created_by) REFERENCES workers(id)
        ON DELETE SET NULL,
    INDEX idx_people_name (full_name),
    INDEX idx_people_phone (phone)
);

CREATE TABLE IF NOT EXISTS followups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    person_id INT NOT NULL,
    followup_date DATE NOT NULL,
    reason VARCHAR(255) NULL,
    status ENUM('Pending', 'Completed', 'Missed') NOT NULL DEFAULT 'Pending',
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_followups_person FOREIGN KEY (person_id) REFERENCES people(id)
        ON DELETE CASCADE,
    INDEX idx_followups_date_status (followup_date, status)
);
