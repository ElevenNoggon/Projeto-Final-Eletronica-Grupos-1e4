import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'pkg_projeto'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.xml')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'audio'), glob('audio/*.mp3')),
        (os.path.join('share', package_name, 'scripts'), glob('scripts/*.sh')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='evelyn',
    maintainer_email='evelynnogueirag@outlook.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'vision = pkg_projeto.vision_node:main',
            'naveg = pkg_projeto.varredura_pf:main',
            'sound = pkg_projeto.sound:main'
        ],
    },
)
