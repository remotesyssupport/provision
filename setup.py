from setuptools import setup, find_packages

setup(
    name='provision',
    version='0.9.3-dev',
    author='genForma Corporation',
    author_email='code@genforma.com',
    url='https://github.com/genforma/provision',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points = {
        'console_scripts': [
            'list-nodes = provision.list:main',
            'deploy-node = provision.deploy:main',
            'destroy-node = provision.destroy:main',
            ]},
    install_requires=['argparse>=1.1',
                      'pycrypto>=2.1.0',
                      'paramiko>=1.7.6',],
    test_suite = 'test',
    license='Apache V2.0',
    description='Create highly customized servers in the cloud',
    long_description=open('README.rst').read(),
    )
