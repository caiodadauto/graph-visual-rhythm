import os
import multiprocessing
import subprocess as sub
from pathlib import Path
from setuptools import setup
from setuptools.command.install import install
from distutils.command.build import build
from distutils.spawn import find_executable


SUMO_SRC = 'https://sourceforge.net/projects/sumo/files/sumo/version 1.2.0/sumo-src-1.2.0.tar.gz'
BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
SHARE_PATH = Path.home().joinpath('.local/share')
BASHRC_PATH = Path.home().joinpath('.bashrc')
SUMO_PATH = BASE_PATH.joinpath('sumo-1.2.0')
BUILD_PATH = SUMO_PATH.joinpath('build/cmake-build')
N_CPU = 4#multiprocessing.cpu_count()

class SumoBuild(build):
    def run(self):
        # run original build code
        build.run(self)

        cmd_mv = ['mv', str(SUMO_PATH), str(SHARE_PATH)]
        cmd_tar = ['tar', '-xzf', 'sumo-1.2.0.tar.gz']
        cmd_wget = ['wget', '-O', BASE_PATH.joinpath('sumo-1.2.0.tar.gz'), SUMO_SRC]
        cmd_cmake = ['cmake', '../..']
        cmd_make = ['make', '-j%s'%N_CPU]

        def compile():
            sub.run(cmd_wget)
            sub.run(cmd_tar, cwd=BASE_PATH)

            os.environ["SUMO_HOME"] = str(SUMO_PATH)
            if not BUILD_PATH.exists():
                os.makedirs(BUILD_PATH)
            sub.run(cmd_cmake, cwd=BUILD_PATH)
            sub.run(cmd_make, cwd=BUILD_PATH)
            sub.run(cmd_mv)

        if not find_executable('sumo'):
            self.execute(compile, [], 'Compiling SUMO')
            path_export = 'export PATH="$PATH:%s"'%(SHARE_PATH.joinpath('sumo-1.2.0/bin'))
            sumo_export = 'export SUMO_HOME="%s"'%(SHARE_PATH.joinpath('sumo-1.2.0'))
            bashrc_text = BASHRC_PATH.read_text()
            if not sumo_export in bashrc_text:
                BASHRC_PATH.write_text('{bashrc_text}\n{path_export}\n{sumo_export}\n'.format(**vars()))
        self.mkpath(self.build_lib)

class SumoInstall(install):
    def initialize_options(self):
        install.initialize_options(self)
        self.build_scripts = None

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        # run original install code
        install.run(self)
        self.copy_tree(self.build_lib, self.install_lib)

# def read(fname):
    # return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='gvr_vanet',
    version='0.1',
    description='Graph Visual Rhythm (GVR) for vehicular networks, considering temporal graphs.',
    maintainer='Caio Dadauto and Silvana Trindade',
    maintainer_email='caio.dadauto@ic.unicamp.br and silvana@lrc.ic.unicamp.br',
    license='GPLv3',
    packages=['gvr_vanet'],
    package_data={
        'gvr_vanet': [
            'traci/*', 'sumolib/*', 'sumolib/files/*',
            'sumolib/net/*', 'sumolib/output/*', 'sumolib/scenario/*',
            'sumolib/sensors/*', 'sumolib/shapes/*', 'sumolib/visualization/*',
            'sumolib/output/convert/*', 'sumolib/scenario/scenarios/*', 'sumolib/scenario/vtypes/*'
        ]
    },
    # long_description=read('README.rst'),
    cmdclass={
        'build': SumoBuild,
        'install': SumoInstall
    }
)
