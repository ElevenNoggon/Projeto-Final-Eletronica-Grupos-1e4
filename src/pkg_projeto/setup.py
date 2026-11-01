from setuptools import find_packages, setup

package_name = 'pkg_projeto'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
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
            'naveg = pkg_projeto.varredura_pf:main'
        ],
    },
)
