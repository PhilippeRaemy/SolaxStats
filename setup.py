from setuptools import setup

setup(
    name="solax",
    version="1.0",
    py_modules=["solax"],
    include_package_data=True,
    install_requires=["click"],
    entry_points="""
        [console_scripts]
        solax=solax:cli
    """,
)
