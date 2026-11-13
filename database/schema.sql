-- WebPulse MySQL 8.x Database Schema
-- Run this script in MySQL Workbench, phpMyAdmin, or mysql CLI:
-- mysql -u root -p < database/schema.sql

CREATE DATABASE IF NOT EXISTS `webpulse_db`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `webpulse_db`;

-- 1. users
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(100) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. websites
CREATE TABLE IF NOT EXISTS `websites` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NULL,
  `name` VARCHAR(150) NOT NULL,
  `url` VARCHAR(2048) NOT NULL,
  `monitoring_interval_seconds` INT NOT NULL DEFAULT 60,
  `timeout_seconds` INT NOT NULL DEFAULT 10,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `description` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `fk_websites_user_id` (`user_id`),
  KEY `idx_websites_active_interval` (`is_active`, `monitoring_interval_seconds`),
  CONSTRAINT `fk_websites_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. monitoring_results
CREATE TABLE IF NOT EXISTS `monitoring_results` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `website_id` INT NOT NULL,
  `checked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `http_status_code` INT NULL,
  `response_time_ms` DOUBLE NULL,
  `is_available` TINYINT(1) NOT NULL,
  `error_type` VARCHAR(100) NULL,
  `error_message` TEXT NULL,
  KEY `fk_results_website_id` (`website_id`),
  KEY `idx_results_checked_at` (`checked_at`),
  KEY `idx_results_avail_checked` (`is_available`, `checked_at`),
  KEY `idx_results_website_checked` (`website_id`, `checked_at`),
  CONSTRAINT `fk_results_website` FOREIGN KEY (`website_id`)
    REFERENCES `websites` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. incidents
CREATE TABLE IF NOT EXISTS `incidents` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `website_id` INT NOT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `resolved_at` DATETIME NULL,
  `duration_seconds` INT NULL,
  `status` VARCHAR(50) NOT NULL DEFAULT 'OPEN',
  `cause_summary` VARCHAR(255) NULL,
  KEY `fk_incidents_website_id` (`website_id`),
  KEY `idx_incidents_status` (`status`),
  KEY `idx_incidents_started_at` (`started_at`),
  KEY `idx_incidents_website_status` (`website_id`, `status`),
  CONSTRAINT `fk_incidents_website` FOREIGN KEY (`website_id`)
    REFERENCES `websites` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. alert_history
CREATE TABLE IF NOT EXISTS `alert_history` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `incident_id` INT NULL,
  `website_id` INT NOT NULL,
  `alert_type` VARCHAR(50) NOT NULL,
  `recipient` VARCHAR(255) NULL,
  `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `delivery_status` VARCHAR(50) NOT NULL,
  `error_message` TEXT NULL,
  KEY `fk_alert_incident_id` (`incident_id`),
  KEY `fk_alert_website_id` (`website_id`),
  KEY `idx_alert_sent_at` (`sent_at`),
  CONSTRAINT `fk_alert_incident` FOREIGN KEY (`incident_id`)
    REFERENCES `incidents` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_alert_website` FOREIGN KEY (`website_id`)
    REFERENCES `websites` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
