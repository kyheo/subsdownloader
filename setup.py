from setuptools import setup, find_packages
setup(
    name = "subsdownloader",
    version = "0.1",
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'subsdownloader= subsdownloader.main:main',
            ], 
        },    
    test_suite = "subsdownloader.test",
    include_package_data = True,
    author = "Martin Marrese",
    author_email = "marrese@gmail.com",
    description = "Subtitle downloader",
)
