# tools/server/hpc.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Wrapper for interaction with HPC.
'''
import paramiko
import os
from scp import SCPClient

from tools.carbon import get_emissions_command_from_job

class HPCInteraction:
    def __init__(self, hostname, username, ssh_key_path, remote_working_directory, local_working_directory):
        self.hostname = hostname
        self.username = username
        self.key_filename = ssh_key_path
        self.client = None
        self.remote_working_directory = remote_working_directory
        self.local_working_directory = local_working_directory


    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.hostname, username=self.username, key_filename=self.key_filename, timeout=5000)

    def disconnect(self):
        if self.client:
            self.client.close()

    def execute_command(self, command):
        if not self.client:
            self.connect()
        stdin, stdout, stderr = self.client.exec_command(command)
        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')

    def submit_job(self, job, slurm_submission):
        if not self.client:
            self.connect()

        # create the remote working directory if it does not exist
        command = f"mkdir -p {self.remote_working_directory}/{job.job_id}"
        self.execute_command(command)
        
        # Transfer all input files
        with SCPClient(self.client.get_transport(), socket_timeout=5000) as scp:
            for file_transfer in slurm_submission.get_file_transfers():
                if file_transfer.is_input:
                    scp.put(file_transfer.local_path, file_transfer.remote_path)
        
        # Generate and transfer the job script
        script_content = slurm_submission.generate_script()
        script_filename = os.path.join(self.local_working_directory, 'submissions', f"job_script_{job.job_id}.sh")
        with open(script_filename, 'w') as f:
            f.write(script_content)
        remote_script_path = f"{self.remote_working_directory}/{job.job_id}/job_script_{job.job_id}.sh"
        with SCPClient(self.client.get_transport()) as scp:
            scp.put(script_filename, remote_script_path)
        
        # Submit the job
        submit_command = f"sbatch {remote_script_path}"
        stdout, stderr = self.execute_command(submit_command)
        
        # Parse job ID from Slurm output
        hpc_job_id = stdout.strip().split()[-1]
        
        # Clean up local script file
        os.remove(script_filename)
        
        return hpc_job_id
    
    def update_all_uncompleted_jobs_status(self, db):
        query = "SELECT job_id, hpc_job_id FROM jobs WHERE status != 'completed' AND status != 'failed'"
        jobs = db.cursor.execute(query).fetchall()

        for job_id, hpc_job_id in jobs:
            status = self.check_job_status(hpc_job_id)
            db.update_job_status(job_id, status)

    def check_job_status(self, hpc_job_id):
        command = f"squeue -j {hpc_job_id} -h -o %t"
        stdout, _ = self.execute_command(command)
        status = stdout.strip()
        
        if not status:
            # Job not in queue, check if it completed
            command = f"sacct -j {hpc_job_id} -o State -n -P"
            stdout, _ = self.execute_command(command)
            status = stdout.strip()
            print(status)
            if status:
                status = stdout.split()[0].lower()
            else:
                return 'failed'
        
        else:
            map = {
                'R': 'running',
                'PD': 'pending',
                'CG': 'completed',
                'F': 'failed'
            }
            status = map.get(status, 'unknown')
        
        return status

    def retrieve_results(self, job, slurm_submission=None):
        if not self.client:
            self.connect()
        
        with SCPClient(self.client.get_transport()) as scp:
            if slurm_submission is not None:
                for file_transfer in slurm_submission.get_file_transfers():
                    if not file_transfer.is_input:
                        scp.get(file_transfer.remote_path, file_transfer.local_path)
            
            # Get the main output file
            remote_output = f"{self.remote_working_directory}/{job.output_filename}"
            local_output = f"{self.local_working_directory}/results/{job.output_filename}"
            scp.get(remote_output, local_output)
    
    def get_carbon_footprint(self, job):
        command = get_emissions_command_from_job(self.remote_working_directory, job)
        stdout, _ = self.execute_command(command)
        return float(stdout.strip())