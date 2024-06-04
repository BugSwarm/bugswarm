from reproducer.reproduce_exception import ReproduceError


def copy_job_files_to_output_dir(job_dispatcher, job):
    # Copy log
    if job_dispatcher.utils.check_if_log_exist(job):
        if job_dispatcher.utils.check_is_bad_log(job):
            raise ReproduceError('Bad log.')
        job_dispatcher.utils.copy_logs_into_current_task_dir(job)

    # Copy job info
    if job_dispatcher.utils.check_if_reproduced_job_info_exist(job):
        job_dispatcher.utils.copy_reproduced_job_info_into_current_task_dir(job)
