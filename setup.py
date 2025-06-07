from setuptools import setup, find_packages
import os, shutil

#移除构建的build文件夹
current_path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(current_path, 'build')
if os.path.isdir(path):
    print('INFO del dir ', path) 
    shutil.rmtree(path)

setup(
    name='ptof',
    version='0.0.1',
    python_requires=">=3.11",
    install_requires = [
        'importlib-metadata; python_version>"3.10"',
        'setuptools',
        'BeautifulSoup4',
        'pypdf[full]',
        'PyMuPDF',
        'pandas',
        'pyyaml',
        'openpyxl',
        'loguru',
        'click',
        'pystray',
    ],
    packages=find_packages(
        where='src',
        include='ptof*',
    ),
    include_package_data=True,  # 包含MANIFEST.in中指定的文件
    package_data={
        # 指定ptof包中的resources目录下的所有文件
        'ptof': ['resources/*', 'resources/*/*'],
    },
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'cli-name = ptof:cli'
        ]
    },
)