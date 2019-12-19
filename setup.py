import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="actionnetwork-activist-sync-bostondsa",
    version="0.0.1",
    author="BostonDSA",
    author_email="tech@bostondsa.org",
    description="Syncs Activists to ActionNetwork",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BostonDSA/actionnetwork_activist_sync",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
