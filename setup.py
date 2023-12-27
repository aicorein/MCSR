from setuptools import setup


with open('requirements.txt') as fp:
    required = fp.read().splitlines()


setup(
    name='mcsr',
    version='1.0.0',
    description='A minecraft server wrapper and refabrication.',
    author='AiCorein',
    author_email='melodyecho@glowmem.com',
    packages=['mcsr'],
    package_dir={
        'mcsr': 'mcsr',
    },
    install_requires=required
)
