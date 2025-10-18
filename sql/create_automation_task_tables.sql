-- SQL script to create automation task tracking tables

CREATE TABLE IF NOT EXISTS automation_tasks (
    id CHAR(36) NOT NULL PRIMARY KEY,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    metadata TEXT NULL,
    result TEXT NULL,
    message TEXT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS automation_task_events (
    id BIGINT NOT NULL AUTO_INCREMENT,
    task_id CHAR(36) NOT NULL,
    status VARCHAR(32) NOT NULL,
    detail TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_automation_task_events_task
        FOREIGN KEY (task_id) REFERENCES automation_tasks(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_automation_task_events_task_id
    ON automation_task_events (task_id);

