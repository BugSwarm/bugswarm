from setuptools import setup, find_packages

setup(
    name='bugswarm',
    version='1.0.0',
    url='https://github.com/BugSwarm/bugswarm',
    author='BugSwarm',
    author_email='dev.bugswarm@gmail.com',

    description='Library of modules used throughout the BugSwarm toolset',
    long_description='Library of modules used throughout the BugSwarm toolset',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
    ],
    zip_safe=False,
    packages=find_packages(),
    install_requires=[
        'wheel==0.33.6',
        'requests>=2.20.0',
        'CacheControl==0.12.3',
        'requests-cache==0.4.13',
        'requests-mock==1.8.0',
        'termcolor==1.1.0',
        'docker==2.5.1',
        'gitpython==3.0.8',
        'python-dateutil==2.8.1',
        'PyYAML==5.2.0',
        'beautifulsoup4==4.8.2',
        'lxml==4.6.3',
        'proxy_requests==0.3.5',
        'packaging==20.7',
        'urllib3==1.25.11',
    ],
)
