# app.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Run this to start the flask server.
'''
import os
from flask import Flask, render_template, request, redirect, url_for, flash, g, send_file
from tools.config_loader import Config
from tools.jobs.job_database import Job, get_db
from tools.server.hpc import HPCInteraction
from tools.submissions.slurm_submission import DummySubmissionWithFileTransfer

from tools.submissions.neuralplexer_submission import NeuralplexerSubmission
from tools.submissions.colabfold_submission import ColabFold2Submission

import tempfile

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, filemode='w', filename='app.log')

app = Flask(__name__)

config = Config()
hpc = HPCInteraction(**config.get_hpc_config())
app.secret_key = config.get('Server', 'secret_key')

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/')
def home():
    protocols = [
        {
            'name': 'Dummy Protocol',
            'description': 'A dummy protocol that demonstrates file transfer and job submission.',
            'url': url_for('submit_dummy')
        },
        {
            'name': 'Neuralplexer',
            'description': 'Predict protein ligand complexes.',
            'url': url_for('submit_neuralplexer')
        },
        {
            'name': 'ColabFold2',
            'description': 'Predict protein structures.',
            'url': url_for('submit_colabfold2')
        }
    ]
    return render_template('home.html', protocols=protocols)

@app.route('/submit_dummy', methods=['GET', 'POST'])
def submit_dummy():
    if request.method == 'POST':
        input_file = request.files['input_file']
        if input_file:
            # Save the file temporarily
            with tempfile.NamedTemporaryFile() as temp_file:
                input_filepath = temp_file.name
                input_file.save(input_filepath)

                # Create job and submission objects
                job = Job(submission_type="dummy", user_id="test_user")  # You might want to implement user authentication
                db = get_db()
                job_id = db.add_job(job)

                slurm_config = config.get_slurm_config()
                submission = DummySubmissionWithFileTransfer(
                    input_filepath=input_filepath,
                    job=job,
                    remote_working_directory=config.get('HPC', 'remote_working_directory'),
                    **slurm_config
                )

                # Submit job to HPC
                try:
                    hpc_job_id = hpc.submit_job(job, submission)
                    db.update_job_hpc_id(job_id, hpc_job_id)
                    flash(f'Job submitted successfully. Job ID: {job_id}', 'success')
                except Exception as e:
                    flash(f'Error submitting job: {str(e)}', 'error')

            return redirect(url_for('job_status', job_id=job_id))

    return render_template('submit_dummy.html')

@app.route('/submit_neuralplexer', methods=['GET', 'POST'])
def submit_neuralplexer():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No CSV file part', 'error')
            return redirect(request.url)
        
        csv_file = request.files['csv_file']
        zip_file = request.files.get('zip_file')  # This is optional
        userid = request.form.get('userid')
        if userid not in config.get('Server', 'accepted_users'):
            raise ValueError('User not authorized to submit jobs')

        if csv_file.filename == '':
            flash('No selected CSV file', 'error')
            return redirect(request.url)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = os.path.join(temp_dir, 'input.csv')
            csv_file.save(csv_path)
            if zip_file:
                zip_path = os.path.join(temp_dir, 'pdb_files.zip')
                zip_file.save(zip_path)
                # unzip them and leave the original zip file
                os.system(f'unzip {zip_path} -d {temp_dir}')
            else:
                # touch a file
                zip_path = os.path.join(temp_dir, 'pdb_files.zip')
                os.system(f'touch {zip_path}')               


            # Validate CSV content
            try:
                with open(csv_path, 'r') as f:
                    header = f.readline().strip()
                    if header != 'protein_seq,smiles,pdb':
                        raise ValueError('Invalid CSV header')
                    for line in f:
                        if len(line.strip().split(',')) != 3:
                            raise ValueError('Invalid CSV format')
                        if line.strip().split(',')[2] not in ['', None] and not os.path.exists(os.path.join(temp_dir, line.strip().split(',')[2])):
                            raise ValueError('PDB file not found')
                # remove all the pdb files now that we have validated them
                os.system(f'rm {temp_dir}/*.pdb')
            except Exception as e:
                raise e

            # Create job and submission objects
            job = Job(submission_type="NeuralPlexer", user_id=userid)  # Implement real user authentication
            db = get_db()
            job_id = db.add_job(job)

            slurm_config = config.get_slurm_config()
            submission = NeuralplexerSubmission(
                csv_path=csv_path,
                zip_path=zip_path,
                job=job,
                remote_working_directory=config.get('HPC', 'remote_working_directory'),
                **slurm_config
            )

            # Submit job to HPC
            try:
                hpc_job_id = hpc.submit_job(job, submission)
                db.update_job_hpc_id(job_id, hpc_job_id)
                flash(f'Job submitted successfully. Job ID: {job_id}', 'success')
            except Exception as e:
                raise e

            return redirect(url_for('job_status', job_id=job_id))

    return render_template('submit_neuralplexer.html')

@app.route('/submit_colabfold2', methods=['GET', 'POST'])
def submit_colabfold2():
    if request.method == 'POST':
        if 'fasta_file' not in request.files:
            flash('No FASTA file part', 'error')
            return redirect(request.url)
        
        fasta_file = request.files['fasta_file']
        userid = request.form.get('userid')
        
        if userid not in config.get('Server', 'accepted_users'):
            flash('User not authorized to submit jobs', 'error')
            return redirect(request.url)

        if fasta_file.filename == '':
            flash('No selected FASTA file', 'error')
            return redirect(request.url)

        if fasta_file:
            with tempfile.TemporaryDirectory() as temp_dir:
                fasta_path = os.path.join(temp_dir, 'input.fasta')
                fasta_file.save(fasta_path)

                # Validate FASTA file content
                try:
                    with open(fasta_path, 'r') as f:
                        if not f.read().startswith('>'):
                            raise ValueError('Invalid FASTA format')
                except Exception as e:
                    flash(f'Invalid FASTA file: {str(e)}', 'error')
                    return redirect(request.url)

                # Create job and submission objects
                job = Job(submission_type="ColabFold2", user_id=userid)
                db = get_db()
                job_id = db.add_job(job)

                slurm_config = config.get_slurm_config()
                submission = ColabFold2Submission(
                    fasta_file_path=fasta_path,
                    job=job,
                    remote_working_directory=config.get('HPC', 'remote_working_directory'),
                    **slurm_config
                )

                # Submit job to HPC
                try:
                    hpc_job_id = hpc.submit_job(job, submission)
                    db.update_job_hpc_id(job_id, hpc_job_id)
                    flash(f'Job submitted successfully. Job ID: {job_id}', 'success')
                except Exception as e:
                    raise ValueError(f'Error submitting job.')

                return redirect(url_for('job_status', job_id=job_id))

    return render_template('submit_colabfold2.html')

@app.route('/job_status')
def job_status():
    job_id = request.args.get('job_id')
    if job_id:
        db = get_db()
        job = db.get_job(job_id)
        hpc_id = job.hpc_job_id
        status = hpc.check_job_status(hpc_id)
        if status == 'completed':
            carbon_footprint = hpc.get_carbon_footprint(job)
            db.update_job_carbon_footprint(job_id, carbon_footprint)
        db.update_job_status(job_id, status)
        job = db.get_job(job_id)
        
        if job:
            # You might want to implement real-time status checking here
            return render_template('job_status.html', job=job)
        else:
            flash('Job not found', 'error')
    return render_template('job_status.html', job=None)

@app.route('/retrieve_results/<int:job_id>')
def retrieve_results(job_id):
    db = get_db()
    job = db.get_job(job_id)
    if job:
        if job.status == 'completed':
            result_path = os.path.join(config.get('HPC', 'local_working_directory'), 'results', job.output_filename)
            print(result_path)
            if os.path.exists(result_path):
                flash('Results already retrieved', 'success')
                return send_file(result_path, as_attachment=True)
            
            try:
                hpc.retrieve_results(job)
                flash('Results retrieved successfully', 'success')
            except Exception as e:
                flash(f'Error retrieving results: {str(e)}', 'error')

            if not os.path.exists(result_path):
                flash('Results not found', 'error')
        else:
            raise ValueError('Please check job status to refresh results.')
        send_file(result_path, as_attachment=True)
        return redirect(url_for('job_status', job_id=job_id))
    else:
        flash('Job not found', 'error')
        return redirect(url_for('job_status', job_id=job_id))
        
        

if __name__ == '__main__':
    app.run(**config.get_server_config())