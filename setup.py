from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='windrpc',
    version='0.1.0',
    description='WindRPC – a lightweight RPC framework using Protocol Buffers and Nanopb for micro systems',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='rollcake',
    author_email='rollcake.dev@gmail.com',
    url='https://github.com/micro-artwork/windrpc',
    license='MIT',
    install_requires=[],
    packages=find_packages(),
    keywords=['RPC', 'protocol buffer', 'nanopb', 'windrpc'],
    python_requires='>=3.6',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'windrpc = windrpc.windrpc_gen:main',
        ],
    },
)
