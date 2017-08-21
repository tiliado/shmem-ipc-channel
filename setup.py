from setuptools import setup, find_packages

setup(
    name="shmemchannel",
    version="0.0.1",
    author="Jiří Janoušek",
    author_email="janousek.jiri@gmail.com",
    description="Python bindings for libshmchannel",
    license="BSD-2-Clause",
    url="https://github.com/tiliado/shmem-ipc-channel",
    packages=find_packages(),
    setup_requires=["cffi>=1.0.0"],
    cffi_modules=["cffibuilders/shmch.py:builder"],
    install_requires=["cffi>=1.0.0"],
)
