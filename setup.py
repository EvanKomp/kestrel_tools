from setuptools import setup, find_packages

setup(
    name='tools',
    version='1.0.0',
    description='A backend and server to wrap tools for NREL users to submit jobs to HPC systems.',
    author='Evan Komp',
    author_email='evankomp@nrel.gov',
    packages=find_packages(),
    install_requires=[
        # Add your project dependencies here
    ],

)