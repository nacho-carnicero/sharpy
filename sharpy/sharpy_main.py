"""sharpy_main: Where it all starts

"""
import dill as pickle
import sharpy.utils.cout_utils as cout


def main(args=None, sharpy_input_dict=None):
    """
    Main ``SHARPy`` routine

    This is the main ``SHARPy`` routine.
    It starts the solution process by reading the settings that are
    included in the ``.sharpy`` file that is parsed
    as an argument, or an equivalent dictionary given as ``sharpy_input_dict``.
    It reads the solvers specific settings and runs them in order

    Args:
        args (str): ``.sharpy`` file with the problem information and settings
        sharpy_input_dict (dict): ``dict`` with the same contents as the
            ``solver.txt`` file would have.

    Returns:
        sharpy.presharpy.presharpy.PreSharpy: object containing the simulation results.

    """
    import time
    import argparse

    import sharpy.utils.input_arg as input_arg
    import sharpy.utils.solver_interface as solver_interface
    from sharpy.presharpy.presharpy import PreSharpy
    from sharpy.utils.cout_utils import start_writer, finish_writer
    import logging
    import os

    import h5py
    import sharpy.utils.h5utils as h5utils

    # Loading solvers and postprocessors
    import sharpy.solvers
    import sharpy.postproc
    import sharpy.generators
    import sharpy.controllers
    # ------------

    try:
        # output writer
        start_writer()
        # timing
        t = time.process_time()
        t0_wall = time.perf_counter()

        if sharpy_input_dict is None:
            parser = argparse.ArgumentParser(prog='SHARPy', description=
            """This is the executable for Simulation of High Aspect Ratio Planes.\n
            Imperial College London 2021""")
            parser.add_argument('input_filename', help='path to the *.sharpy input file', type=str, default='')
            parser.add_argument('-r', '--restart', help='restart the solution with a given snapshot', type=str,
                                default=None)
            parser.add_argument('-d', '--docs', help='generates the solver documentation in the specified location. '
                                                     'Code does not execute if running this flag', action='store_true')
            if args is not None:
                args = parser.parse_args(args[1:])
            else:
                args = parser.parse_args()

        if args.docs:
            import subprocess
            import sharpy.utils.docutils as docutils
            import sharpy.utils.sharpydir as sharpydir
            docutils.generate_documentation()

            # run make
            cout.cout_wrap('Running make html in sharpy/docs')
            subprocess.Popen(['make', 'html'],
                             stdout=None,
                             cwd=sharpydir.SharpyDir + '/docs')

            return 0

        if args.input_filename == '':
            parser.error('input_filename is a required argument of SHARPy.')
        settings = input_arg.read_settings(args)
        if args.restart is None:
            # run preSHARPy
            data = PreSharpy(settings)
        else:
            try:
                with open(args.restart, 'rb') as restart_file:
                    data = pickle.load(restart_file)
            except FileNotFoundError:
                raise FileNotFoundError('The file specified for the snapshot \
                    restart (-r) does not exist. Please check.')


            # update the settings
            data.update_settings(settings)

            # Read again the dyn.h5 file
            data.structure.dynamic_input = []
            dyn_file_name = data.case_route + '/' + data.case_name + '.dyn.h5'
            if os.path.isfile(dyn_file_name):
                fid = h5py.File(dyn_file_name, 'r')
                data.structure.dyn_dict = h5utils.load_h5_in_dict(fid)
            # for it in range(self.num_steps):
            #     data.structure.dynamic_input.append(dict())

        # Loop for the solvers specified in *.sharpy['SHARPy']['flow']
        for solver_name in settings['SHARPy']['flow']:
            solver = solver_interface.initialise_solver(solver_name)
            solver.initialise(data)
            data = solver.run()

        cpu_time = time.process_time() - t
        wall_time = time.perf_counter() - t0_wall
        cout.cout_wrap('FINISHED - Elapsed time = %f6 seconds' % wall_time, 2)
        cout.cout_wrap('FINISHED - CPU process time = %f6 seconds' % cpu_time, 2)
        finish_writer()

    except Exception as e:
        try:
            logdir = settings['SHARPy']['log_folder'] + '/' + settings['SHARPy']['case']
        except KeyError:
            logdir = './'
        except NameError:
            logdir = './'
        logdir = os.path.abspath(logdir)
        cout.cout_wrap(('Exception raised, writing error log in %s/error.log' % logdir), 4)
        logging.basicConfig(filename='%s/error.log' % logdir,
                            filemode='w',
                            format='%(asctime)s-%(levelname)s-%(message)s',
                            datefmt='%d-%b-%y %H:%M:%S',
                            level=logging.INFO)
        logging.info('SHARPy Error Log')
        logging.error("Exception occurred", exc_info=True)
        raise e

    return data
