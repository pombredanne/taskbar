import os
from setuptools import setup

try:
    with open('README.md') as file:
        long_description = file.read()
except:
    long_description = "Celery Task progressbar for Django"


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(name='taskbar',
      version='0.1.0',
      description='Celery Task progressbar for Django',
      url='https://github.com/seperman/taskbar',
      download_url='https://github.com/seperman/taskbar/tarball/master',
      author='Seperman',
      author_email='sep@zepworks.com',
      license='MIT',
      packages=['taskbar'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "django",
      ],
      long_description=long_description,
      classifiers=[
          'Environment :: Web Environment',
          'Framework :: Django',
          'License :: MIT License',
          "Intended Audience :: Developers",
          "Operating System :: OS Independent",
          "Topic :: Software Development",
          'Programming Language :: Python',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ],
      )
