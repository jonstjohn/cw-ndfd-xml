import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cw_ndfd_xml",
    version="0.1.0",
    author="Jon St John",
    author_email="jon@element128.com",
    description="Climbing Weather NDFD XML",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jonstjohn/cw-ndfd-xml",
    project_urls={
        "Bug Tracker": "https://github.com/jonstjohn/cw-ndfd-xml/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=[
        'cw_entity',
        'requests'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
)