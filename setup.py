from setuptools import setup, find_packages

setup(
    name='portainer',
    packages=find_packages(),

    install_requires=['docopt', 'pyyaml', 'requests'],

    entry_points={
        'console_scripts': ['portainer=portainer:main'],
    },
)
