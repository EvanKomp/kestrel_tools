# tools/config_loader.py
'''
* Author: Evan Komp
* Created: 7/1/2024
* Company: National Renewable Energy Lab, Bioeneergy Science and Technology
* License: MIT
'''
import configparser
import os

class Config:
    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        self.config.read(config_path)

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        return self.config.getint(section, key, fallback=fallback)

    def getboolean(self, section, key, fallback=None):
        return self.config.getboolean(section, key, fallback=fallback)

    def get_hpc_config(self):
        return {
            'hostname': self.get('HPC', 'hostname'),
            'username': self.get('HPC', 'username'),
            'ssh_key_path': self.get('HPC', 'ssh_key_path'),
            'remote_working_directory': self.get('HPC', 'remote_working_directory'),
            'local_working_directory': self.get('HPC', 'local_working_directory')
        }

    def get_slurm_config(self):
        return {
            'cpu_partition': self.get('Slurm', 'cpu_partition'),
            'gpu_partition': self.get('Slurm', 'gpu_partition'), 
            'gres': self.get('Slurm', 'gres'), 
            'account': self.get('Slurm', 'account'),
            'time_limit': self.get('Slurm', 'time_limit'),
            'nodes': self.getint('Slurm', 'nodes'),
            'ntasks_per_node': self.getint('Slurm', 'ntasks_per_node'),
            'mem': self.get('Slurm', 'mem')
        }

    def get_server_config(self):
        return {
            'host': self.get('Server', 'host'),
            'port': self.getint('Server', 'port'),
            'debug': self.getboolean('Server', 'debug'),
            'secret_key': self.get('Server', 'secret_key')
        }

    def get_database_path(self):
        return self.get('Database', 'path')
