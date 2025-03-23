from setuptools import setup, find_packages

setup(
    name='mtp-file-sync',
    version='0.1.0',
    description='MTP File Synchronization Tool',
    author='Your Name',
    author_email='your@email.com',
    url='https://github.com/yourusername/mtp-file-sync',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'mtp-file-sync = mtp_file_sync.__main__:main'
        ]
    },
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)