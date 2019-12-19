import time

from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN


def get_artifacts():
    t_start = time.time()
    with open("url_list.tsv", "w") as f:
        bugswarmapi = DatabaseAPI(DATABASE_PIPELINE_TOKEN)
        arts = bugswarmapi.list_artifacts()
        for art in arts:
            failed_sha = art['failed_job']['trigger_sha']
            passed_sha = art['passed_job']['trigger_sha']
            repo = art['repo']
            img_tag = art['image_tag']

            f.write(img_tag + '\t' + repo + '\t' + failed_sha + '\t' + passed_sha + '\t' + '\n')
    t_stop = time.time()
    total_time = t_stop - t_start
    print("total time:", total_time)


def main():
    get_artifacts()


if __name__ == "__main__":
    main()
