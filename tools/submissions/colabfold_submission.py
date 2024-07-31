# tools/submissions/colabfold_submission.py
'''
* Author: Evan Komp
* Created: 7/2/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Submit search and inference using colabfold
'''
from tools.submissions.slurm_submission import SlurmSubmission

class ColabFold2Submission(SlurmSubmission):
    def __init__(self, fasta_file_path, **kwargs):
        super().__init__(**kwargs)
        self.add_file_transfer(fasta_file_path, f"{self.remote_working_directory}/input.fasta")

    def _generate_header(self):
        """We have two headers - one for search and one for inference."""

        search_header = f"""#!/bin/bash
#SBATCH --partition={self.cpu_partition}
#SBATCH --account={self.account}
#SBATCH --time=0-23:30:00
#SBATCH --nodes={self.nodes}
#SBATCH --cpus-per-task=100
#SBATCH --mem=240G
#SBATCH --output={self.remote_working_directory}/search.out
"""
        
        inference_header = f"""#!/bin/bash
#SBATCH --partition={self.gpu_partition}
#SBATCH --account={self.account}
#SBATCH --time=0-12:30:00
#SBATCH --nodes=1
#SBATCH --gres={self.gres}
#SBATCH --mem=96G
SBATCH --output={self.remote_working_directory}/inference.out
"""
        return [search_header, inference_header]
    
    def _generate_script(self):
        """Also two scripts, one for inference and one for search."""

        search_script = f"""
module load gcc
/projects/proteinml/software/colabfold_code/submit_search.sh {self.remote_working_directory}/input.fasta {self.remote_working_directory}/search
"""
        
        inference_script = f"""
/projects/proteinml/software/colabfold_code/submit_loop_inference.sh {self.remote_working_directory}/search {self.remote_working_directory}/inference

# zip up the results
tar -czvf {self.remote_working_directory}/{self.get_output_filename()} {self.remote_working_directory}/inference
"""
        return [search_script, inference_script]
