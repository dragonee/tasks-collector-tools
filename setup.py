from setuptools import setup, find_packages

setup(
    name='tasks_collector_tools',
    version='1.0.0',
    description='CLI support for the Tasks Collector application',
    author='Michał Moroz <michal@makimo.pl>',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    packages=('tasks_collector_tools', 'tasks_collector_tools.config'),
    package_dir={'': 'src'},
    install_requires=['docopt', 'requests', 'python-slugify', 'pyyaml', 'colored', 'more-itertools', 'python-dateutil'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'observation = tasks_collector_tools.observation:main',
            'boardmd = tasks_collector_tools.boardmd:main',
            'observationdump = tasks_collector_tools.observationdump:main',
            'quest = tasks_collector_tools.quest:main',
            'addtask = tasks_collector_tools.addtask:main',
            'update = tasks_collector_tools.update:main',
            'journal = tasks_collector_tools.journal:main',
        ],
    }
)
