from setuptools import setup, find_packages

setup(
    name='mcp_postgres',
    version='1.0.2',
    author='Leonardo Sousa',
    author_email='leokaique7@gmail.com',
    description='Uma Ferramenta de Consulta de Bases de Dados PostgreSQL usando Linguagem Natural',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=[
        'requirements.txt'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    
)