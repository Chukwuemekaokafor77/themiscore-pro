from setuptools import setup, find_packages

setup(
    name="legalintake",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'python-dotenv',
        'flask-sqlalchemy',
        'flask-migrate',
        'psycopg2-binary',
        'python-dateutil',
        'werkzeug',
    ],
    python_requires='>=3.8',
)
