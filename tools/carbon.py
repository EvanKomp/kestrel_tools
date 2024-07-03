# tools/carbon.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT

Tools for carobn tracking
'''

def get_emissions_command_from_job(working_directory, job):
    """
    Params
    ------
    working_directory: str
        The working directory of the job on the remote cluster
    job: Job
        The job to get the emissions command for
    """
    # emissiosn are in the fifth column of the second row of emmissions.csv
    return f"awk -F, 'NR > 1 {{sum += $5}} END {{print sum}}' {working_directory}/{job.job_id}/emissions.csv"