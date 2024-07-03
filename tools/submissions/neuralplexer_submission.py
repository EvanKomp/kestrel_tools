# tools/submissions/neuralplexer_submission.py
'''
* Author: Evan Komp
* Created: 7/2/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Wrapper for neuralplexer submission.
'''
from tools.submissions.slurm_submission import SlurmSubmission

class NeuralplexerSubmission(SlurmSubmission):
    def __init__(self, csv_path, zip_path, **kwargs):
        super().__init__(**kwargs)
        self.add_file_transfer(csv_path, f"{self.remote_working_directory}/input.csv")
        if zip_path:
            self.add_file_transfer(zip_path, f"{self.remote_working_directory}/pdb_files.zip")

    def _generate_header(self):
        script = f"""#!/bin/bash
#SBATCH --partition={self.gpu_partition}
#SBATCH --reservation=h100-testing
#SBATCH --account={self.account}
#SBATCH --time={self.time_limit}
#SBATCH --nodes={self.nodes}
#SBATCH --mem={self.mem}
#SBATCH --gres={self.gres}
#SBATCH --output={self.remote_working_directory}/slurm.out
"""  
        return script
    
    def _generate_script(self):
        return '''
# Unzip PDB files if they exist
if [ -f pdb_files.zip ]; then
    unzip pdb_files.zip
fi

module load cuda
source ~/.bash_profile
conda activate neuralplexer_dev

# function for one call
run_neuralplexer() {
    local INPUT_RECEPTOR_STRING="$1"
    local INPUT_LIGAND_STRING="$2"
    local INPUT_PDB="$3"
    local OUTPUT_FILE="$4"

    if [ -z "$INPUT_PDB" ] || [ "$INPUT_PDB" = "NA" ]; then
        neuralplexer-inference --task=batched_structure_sampling \\
                               --input-receptor "$INPUT_RECEPTOR_STRING" \\
                               --input-ligand "$INPUT_LIGAND_STRING" \\
                               --out-path "$OUTPUT_FILE" \\
                               --model-checkpoint /projects/proteinml/datasets/neuralplexer/neuralplexermodels_downstream_datasets_predictions/models/complex_structure_prediction.ckpt \\
                               --n-samples 10 \\
                               --chunk-size 1 \\
                               --num-steps 100 \\
                               --cuda \\
                               --sampler=langevin_simulated_annealing
    else
        neuralplexer-inference --task=batched_structure_sampling \\
                               --input-receptor "$INPUT_RECEPTOR_STRING" \\
                               --input-ligand "$INPUT_LIGAND_STRING" \\
                               --out-path "$OUTPUT_FILE" \\
                               --model-checkpoint /projects/proteinml/datasets/neuralplexer/neuralplexermodels_downstream_datasets_predictions/models/complex_structure_prediction.ckpt \\
                               --n-samples 10 \\
                               --chunk-size 1 \\
                               --num-steps 100 \\
                               --cuda \\
                               --sampler=langevin_simulated_annealing \\
                               --use-template \\
                               --input-template "$INPUT_PDB"
    fi
}
COUNTER=0
while IFS=',' read -r receptor_seq ligand_smiles pdb_file || [ -n "$receptor_seq" ]; do
    # Remove any surrounding quotes and whitespace
    receptor_seq=$(echo "$receptor_seq" | sed 's/^[[:space:]"]*//;s/[[:space:]"]*$//')
    ligand_smiles=$(echo "$ligand_smiles" | sed 's/^[[:space:]"]*//;s/[[:space:]"]*$//')
    pdb_file=$(echo "$pdb_file" | sed 's/^[[:space:]"]*//;s/[[:space:]"]*$//')

    # Generate a unique output file name
    output_file="output/result_$(printf "%04d" $COUNTER)"
    COUNTER=$((COUNTER+1))

    # Run Neuralplexer for this input
    run_neuralplexer "$receptor_seq" "$ligand_smiles" "$pdb_file" "$output_file"

done < <(tail -n +2 input.csv)  # Skip the header row
''' + f'''
# zip up the results into the expected format
tar -czvf {self.remote_working_directory}/{self.get_output_filename()} output

# clean up
rm -rf *.pdb
'''