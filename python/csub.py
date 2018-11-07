import os
import time
import shutil
import subprocess
import re
# cannot use htcondor python binding because CMS python environment does not have the libraries

class CondorSubmit(object):

    def __init__(self, executable):
        self.executable = executable
        self.hold_on_fail = False
        self.requirements = ''
        self.os = ''
        self.arch = 'X86_64'
        self.group = 'group_u_CMS.u_zh'
        self.flavour = 'espresso'
        self.aux_input = []
        self.request_cpus = 1
        self.request_memory = 100
        self.num_repeats = 1
        self.append_step = True

        self.job_args = []
        self.pre_args = ''
        self.post_args = ''

        self.job_names = []

        self.logdir = '/tmp'
        self.clear_log = False

        self.last_submit = [] # [(cluster id, job name)] of last submit if job_names are set

    def submit(self, name = ''):
        if name:
            logdir = self.logdir +'/' + name
        else:
            logdir = self.logdir + '/' + str(int(time.time()))

        if self.clear_log:
            try:
                shutil.rmtree(logdir)
            except:
                pass

        try:
            os.makedirs(logdir)
        except OSError:
            if not os.path.isdir(logdir):
                raise

        if len(self.job_args) != 0:
            job_args = list(self.job_args)
            use_job_names = (len(set(self.job_names)) == len(job_args))
        else:
            job_args = []
            use_job_names = False

        with open(logdir + '/env.sh', 'w') as envfile:
            for key, value in os.environ.items():
                if key in ['PWD', 'OLDPWD', 'TMPDIR']:
                    continue
                elif key.startswith('BASH_FUNC_'):
                    envfile.write(key.replace('BASH_FUNC_', '') + ' ' + value[2:] + '\n')
                    envfile.write('export -f ' + key.replace('BASH_FUNC_', '').replace('()', '') + '\n')
                else:
                    envfile.write('export ' + key + '="' + value.replace('"', '\\"') + '"\n')

        with open(logdir + '/jobs.dat', 'w') as jobs_file:
            jobs_file.write('[EXECUTABLE] ' + os.path.realpath(self.executable) + '\n')
            jobs_file.write('[NJOBS_PER_ARG] ' + str(self.num_repeats) + '\n')
            if len(job_args) != 0:
                jobs_file.write('[ARGUMENTS]\n')
                for ijob, job_arg in enumerate(job_args):
                    if use_job_names:
                        jobs_file.write('%s: %s\n' % (self.job_names[ijob], job_arg))
                    else:
                        jobs_file.write('%d: %s\n' % (ijob, job_arg))

        with open(logdir + '/csub.exec', 'w') as wrapper:
            # Condor executable - sources env.sh and switches process image to the executable
            wrapper.write('#!/bin/bash\n\nsource env.sh\nEXECUTABLE=$1\nshift\nARGS="$@"\nexec $EXECUTABLE $ARGS\n')

        jdl = []
        jdl.append(('executable', logdir + '/csub.exec'))
        jdl.append(('universe', 'vanilla'))
        jdl.append(('should_transfer_files', 'YES'))
        jdl.append(('input', '/dev/null'))
        requirements = ['Arch == "%s"' % self.arch]
        if self.requirements:
            requirements.append(self.requirements)
        if self.os:
            jdl.append(('+REQUIRED_OS', '"%s"' % self.os))
            requirements.append('OpSysAndVer == "%s" || HasSingularity =?= true' % self.os)

        jdl.append(('requirements', ' && '.join(['(%s)' % r for r in requirements])))
        jdl.append(('rank', '32 - TARGET.SlotID')) # evenly distribute jobs across machines

        input_files = [logdir + '/env.sh'] + self.aux_input
        jdl.append(('transfer_input_files', ','.join(input_files)))

        jdl.append(('transfer_output_files', '""'))
        jdl.append(('accounting_group', self.group))
        jdl.append(('+AccountingGroup', self.group))
        jdl.append(('+JobFlavour', '"%s"' % self.flavour))
        jdl.append(('request_cpus', self.request_cpus))
        jdl.append(('request_memory', self.request_memory))
        if self.hold_on_fail:
            jdl.append(('on_exit_hold', '(ExitBySignal == True) || (ExitCode != 0)'))
       
        if use_job_names:
            jdl.append(('log', logdir + '/$(Cluster).$(JobName).log'))
            jdl.append(('output', logdir + '/$(Cluster).$(JobName).out'))
            jdl.append(('error', logdir + '/$(Cluster).$(JobName).err'))
        else:
            jdl.append(('log', logdir + '/$(Cluster).$(Process).log'))
            jdl.append(('output', logdir + '/$(Cluster).$(Process).out'))
            jdl.append(('error', logdir + '/$(Cluster).$(Process).err'))

        arg = '"' + os.path.realpath(self.executable)

        arg += ' ' + self.pre_args

        if len(job_args) != 0:
            arg += ' $(JobArgs)'

        arg += ' ' + self.post_args

        if self.num_repeats > 1 and self.append_step:
            arg += ' $(Step)'

        arg += '"'

        jdl.append(('arguments', arg))

        jdl_text = ''.join(['%s = %s\n' % (key, str(value)) for key, value in jdl])
        jdl_text += 'queue %d ' % self.num_repeats

        if len(job_args) != 0:
            if use_job_names:
                jdl_text += 'JobName,'

            jdl_text += 'JobArgs from (\n'
    
            for ijob, job_arg in enumerate(job_args):
                if use_job_names:
                    jdl_text += self.job_names[ijob] + ', '
    
                if ijob == 0 and job_arg.strip() == '':
                    # condor bug? cannot handle empty argument in the first line
                    jdl_text += '_DUMMY_\n'
                else:
                    jdl_text += job_arg + '\n'
    
            jdl_text += ')'

        jdl_text += '\n'

        with open(logdir + '/jdl', 'w') as jdl_file:
            jdl_file.write(jdl_text)

        proc = subprocess.Popen(['condor_submit'], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        out, err = proc.communicate(jdl_text)
        print out.strip()

        matches = re.search('job\(s\) submitted to cluster ([0-9]+)\.', out)
        if matches:
            cluster_id = int(matches.group(1))
            if use_job_names:
                self.last_submit = []
                for ijob, job_name in enumerate(self.job_names):
                    self.last_submit.append(('%d.%d' % (cluster_id, ijob), job_name))
        else:
            print 'No cluster id found!'
            cluster_id = 0
    
        print 'Logdir is', logdir
 
        return cluster_id
