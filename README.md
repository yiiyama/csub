Basic usage
===========

`csub <command> -a "<arguments_job1>" "<arguments_job2>" ...`

submits condor jobs that execute <command> with <arguments_job1> for the first job, <arguments_job2> for the second, ...
<command> must be executable as is by the worker nodes (i.e. should be full paths or something in $PATH).

Job environment
===============

All environment of the current shell (except for PWD) is inherited in the batch jobs. As with any condor jobs, the jobs will start in a temporary working area local to the batch worker node.

Alternative submission modes
============================

* Just create multiple copies of the same command

   `csub <command> -n <N>`
   
   <N> is the number of jobs.
* Read the list of arguments from a file

   `csub <command> -i <PATH>`
   
   File must contain arguments for one job per line.
   
Options `-a` and `-i` cannot be combined, but the other combinations are possible (e.g. submit N copies of each job in the arguments file)

Options that affect the executable
==================================

* Submit multi-argument jobs where the first (last) few arguments are common

   `csub <command> -e "<first_args>" -t "<last_args>" -a "<arguments_job1>" "<arguments_job2>" ...`
   
   submits jobs that execute `<command> <first_args> <arguments_job1> <last_args>`, `<command> <first_args> <arguments_job2> <last_args>`, ...
* Ship auxiliary input files with jobs

   `csub <command> -x <file1> <file2> ...`
   
   This option is useful when you need the jobs to have access to your grid proxy, for example. All files will be placed in the jobs' initial working directories.
   
Job submission options
======================

`--requirements, --os, --group, --flavour, --cpu, --memory, --exclude-host`

Log output
==========

.out, .err, and .log files are written to <logdir>/<tag> where <logdir> is specified by option `--log-dir` (defaule $HOME/csublogs) and <tag> is either the UNIX timestamp of the submission time or the string passed as `--name`.
