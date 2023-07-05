from reproducer.reproduce_exception import ReproduceError


def copy_log(job_dispatcher, job):
    if job_dispatcher.utils.check_if_log_exist(job):
        if job_dispatcher.utils.check_is_bad_log(job):
            raise ReproduceError('Bad log.')
        job_dispatcher.utils.copy_logs_into_current_task_dir(job)
