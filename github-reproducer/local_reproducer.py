import subprocess
import getpass

if __name__ == '__main__':
    _THREADS = 2
    work_directory = '/home/vagrant/bugswarm/wd'
    miner_projects_file_path = '/home/vagrant/bugswarm/wd/project_tags.txt'
    reproducer_input_file_path = '/home/vagrant/bugswarm/wd/project_reproducer_infos.txt'
    clean_cmd = ['sudo', 'docker', 'system', 'prune', '-a', '-f']

    generate_project_reproducer_infos_cmd = ['python3', '/home/vagrant/bugswarm/batch/batch/tasks/bugswarm_reproducer'
                                                        '/generate_pair_input.py', '--repo-file',
                                             miner_projects_file_path, '-o', reproducer_input_file_path,
                                             '--include-resettable', '--include-archived-only'
                                             ]
    result = subprocess.run(generate_project_reproducer_infos_cmd, stdout=subprocess.PIPE, universal_newlines=True)

    with open(reproducer_input_file_path) as f:
        project_reproducer_infos = [line.rstrip('\n').lstrip('\ufeff') for line in f]

    for project_reproducer_info in project_reproducer_infos:
        project_reproducer_info = project_reproducer_info.split(',')
        project_repo = project_reproducer_info[0]
        project_failed = project_reproducer_info[1]
        project_passed = project_reproducer_info[2]
        reproducer_output_file = 'Reproducer_out_{}_{}_{}.txt'.format(project_repo.replace('/', '-'), project_failed,
                                                                      project_passed)
        run_reproducer_cmd = 'touch {0}/{1} && ' \
                             'date >> {0}/{1} && ' \
                             'cd /home/vagrant/bugswarm/reproducer/ && ' \
                             'sudo git clean -d -x -f -f && ' \
                             'sudo bash run_reproduce_pair_alt.sh -r {2} -f {3} -p {4} -t {5} -c ' \
                             '/home/vagrant/bugswarm >> {0}/{1}'.format(
                                 work_directory,
                                 reproducer_output_file,
                                 project_repo,
                                 project_failed,
                                 project_passed,
                                 _THREADS
                             )
        pipeline_reproducer_cmd = ['sudo', 'su', '-l', getpass.getuser(), '-c', run_reproducer_cmd]
        clean_result = subprocess.run(clean_cmd, stdout=subprocess.PIPE, universal_newlines=True)
        reproducer_result = subprocess.run(pipeline_reproducer_cmd, stdout=subprocess.PIPE, universal_newlines=True)
