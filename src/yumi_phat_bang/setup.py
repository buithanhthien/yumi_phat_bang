from glob import glob
from setuptools import setup

package_name = 'yumi_phat_bang'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        *[(f'share/{package_name}/{directory}', glob(f'{directory}/{pattern}'))
          for directory, pattern in [
              ('launch', '*.launch.py'), ('urdf', '*.urdf'),
              ('meshes', '*.STL'), ('rviz', '*.rviz'),
              ('config', '*.yaml'), ('worlds', '*.sdf'), ('docs', '*.md'),
              ('maps', '*.yaml'), ('maps', '*.pgm')]],
    ],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': [
            'wasd_teleop = yumi_phat_bang.wasd_teleop:main',
        ],
    },
    zip_safe=True,
    maintainer='Khoa',
    maintainer_email='khoa@example.com',
    description='Yumi mobile base description and simulation',
    license='Proprietary',
)
