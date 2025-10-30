import setuptools

setuptools.setup(
    name="energy_balance_evaluation",
    version="0.0.1",
    author="Max Nutz",
    author_email="max.nutz@boku.ac.at",
    description="A package for analyzation and evaluation of energy flows in pypsa networks.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/maxnutz/energy_balance_evaulation",
    python_requires=">=3.8",
    packages=["energy_balance_evaluation"],
)
