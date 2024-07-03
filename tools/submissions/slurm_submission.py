# tools/submissions/slurm_submission.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Base class representing a slurm submission.
'''
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FileTransfer:
    local_path: str
    remote_path: str
    is_input: bool = True


class SlurmSubmission(ABC):
    def __init__(
            self,
            remote_working_directory,
            job,
            cpu_partition,
            gpu_partition,
            gres,
            account, 
            time_limit,
            nodes,
            ntasks_per_node,
            mem
    ):
        self.remote_working_directory = f"{remote_working_directory}/{job.job_id}"
        self.job = job
        self.cpu_partition = cpu_partition
        self.gpu_partition = gpu_partition
        self.gres = gres
        self.account = account
        self.time_limit = time_limit
        self.nodes = nodes
        self.ntasks_per_node = ntasks_per_node
        self.mem = mem
        self.files_to_transfer: List[FileTransfer] = []

    @abstractmethod
    def _generate_script(self):
        pass

    @abstractmethod
    def _generate_header(self):
        pass

    def generate_script(self):
        header = self._generate_header()
        script = self._generate_script()

        preamble = f"""cd {self.remote_working_directory}"""+"""
############### CARBON TRACKING
# start codecarbon
PID=$(/projects/proteinml/software/carbon/start_tracker.sh)
echo main
echo $PID
# Save its PID

# Define a cleanup function
cleanup() {
    echo "Cleaning up..."
    kill -SIGINT $PID
    sleep 10
}
# # Set the trap
trap cleanup EXIT
#################### END CARBON TRACKING
source ~/.bash_profile
"""
        if type(script) == str:
            return [header + preamble + script]
        elif type(script) == list:
            scripts = []
            for i, s in enumerate(script):
                scripts.append(header[i] + preamble + s)
            return scripts

    def get_output_filename(self):
        return self.job.output_filename

    def add_file_transfer(self, local_path, remote_path, is_input=True):
        self.files_to_transfer.append(FileTransfer(local_path, remote_path, is_input))

    def get_file_transfers(self):
        return self.files_to_transfer
    

class DummySubmissionWithFileTransfer(SlurmSubmission):

    def __init__(self, input_filepath, **kwargs):
        super().__init__(**kwargs)
        self.add_file_transfer(input_filepath, f"{self.remote_working_directory}/input_file")

    def _generate_header(self):
        return f"""#!/bin/bash
#SBATCH --partition={self.cpu_partition}
#SBATCH --account={self.account}
#SBATCH --time={self.time_limit}
#SBATCH --nodes={self.nodes}
#SBATCH --ntasks-per-node={self.ntasks_per_node}
#SBATCH --mem={self.mem}
#SBATCH --job-name={self.job.job_id}
#SBATCH --output={self.remote_working_directory}/slurm.out
"""

    def _generate_script(self):
        return f"""
# Dummy script
sleep 10
# create output file
touch {self.remote_working_directory}/{self.get_output_filename()}
"""
    