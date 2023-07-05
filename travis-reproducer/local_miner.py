import subprocess
import getpass

if __name__ == '__main__':
    _THREADS = 2
    work_directory = '/home/vagrant/bugswarm/wd'
    miner_input_file_path = '/home/vagrant/bugswarm/wd/project_tags.txt'
    clean_cmd = ['sudo', 'docker', 'system', 'prune', '-a', '-f']
    with open(miner_input_file_path) as f:
        project_tags = [line.rstrip('\n').lstrip('\ufeff') for line in f]

    for project_tag in project_tags:
        miner_output_file = 'Mine_Project_out_{}.txt'.format(project_tag.replace('/', '-'))
        run_miner_cmd = 'touch {0}/{1} && ' \
                        'date >> {0}/{1} && ' \
                        'cd /home/vagrant/bugswarm/pair-finder/ && ' \
                        'sudo git clean -d -x -f -f && ' \
                        'cd /home/vagrant/bugswarm/pair-filter/ && ' \
                        'sudo git clean -d -x -f -f && ' \
                        'cd /home/vagrant/bugswarm/reproducer/ && ' \
                        'sudo git clean -d -x -f -f && ' \
                        'sudo bash run_mine_project.sh -r {2} -t {3} -c /home/vagrant/bugswarm >> {0}/{1}'.format(
                            work_directory,
                            miner_output_file,
                            project_tag,
                            _THREADS
                        )
        pipeline_miner_cmd = ['sudo', 'su', '-l', getpass.getuser(), '-c', run_miner_cmd]
        clean_result = subprocess.run(clean_cmd, stdout=subprocess.PIPE, universal_newlines=True)
        miner_result = subprocess.run(pipeline_miner_cmd, stdout=subprocess.PIPE, universal_newlines=True)
