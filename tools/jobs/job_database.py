# tools/jobs/job_database.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

API to interact with SQlite database for slurm job tracking.
'''
import os
import sqlite3
from enum import Enum
from datetime import datetime

from flask import g
from tools.config_loader import Config

config=Config()

def get_db():
    if 'db' not in g:
        g.db = JobDatabase(config.get_database_path())
    return g.db

class JobDatabase:
    def __init__(self, db_path='jobs.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hpc_job_id INTEGER,
            status TEXT,
            submission_type TEXT,
            user_id TEXT,
            submission_time TIMESTAMP,
            last_updated TIMESTAMP,
            output_filename TEXT,
            carbon_footprint REAL     
        )
        ''')
        self.conn.commit()

    def add_job(self, job):
        self.cursor.execute('''
        INSERT INTO jobs (hpc_job_id, status, submission_type, user_id, submission_time, last_updated, output_filename, carbon_footprint)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job.hpc_job_id, job.status, job.submission_type, job.user_id, job.submission_time, job.last_updated, job.output_filename, job.carbon_footprint))
        self.conn.commit()
        job.job_id = self.cursor.lastrowid
        # update the output filename with the job_id
        self.cursor.execute('''
        UPDATE jobs SET output_filename = ? WHERE job_id = ?
        ''', (job.output_filename, job.job_id))
        return self.cursor.lastrowid

    def update_job_status(self, job_id, status):
        self.cursor.execute('''
        UPDATE jobs SET status = ?, last_updated = ? WHERE job_id = ?
        ''', (status, datetime.now(), job_id))
        self.conn.commit()

    def update_job_hpc_id(self, job_id, hpc_job_id): 
        self.cursor.execute('''
        UPDATE jobs SET hpc_job_id = ? WHERE job_id = ?
        ''', (hpc_job_id, job_id))
        self.conn.commit()

    def update_job_carbon_footprint(self, job_id, carbon_footprint):
        self.cursor.execute('''
        UPDATE jobs SET carbon_footprint = ? WHERE job_id = ?
        ''', (carbon_footprint, job_id))
        self.conn.commit()

    def get_job(self, job_id):
        self.cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
        vals = self.cursor.fetchone()
        if vals is None:
            raise ValueError(f"Job with ID {job_id} not found.")
        job = Job()
        job.job_id = vals[0]
        job.hpc_job_id = vals[1]
        job.status = vals[2]
        job.submission_type = vals[3]
        job.user_id = vals[4]
        job.submission_time = vals[5]
        job.last_updated = vals[6]
        job.carbon_footprint = vals[8]
        return job

    def close(self):
        self.conn.close()

class JobStatus(Enum):
    UNSUBMITTED = "unsubmitted"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    def __init__(self, submission_type=None, user_id=None):
        self.job_id = None
        self.hpc_job_id = None
        self.status = JobStatus.UNSUBMITTED.value
        self.submission_type = submission_type
        self.user_id = user_id
        self.submission_time = datetime.now()
        self.last_updated = datetime.now()
        self.carbon_footprint = None

    def update_status(self, new_status):
        self.status = new_status
        self.last_updated = datetime.now()

    @property
    def output_filename(self):
        return f"{self.submission_type}_{self.job_id}.tar.gz"