import datetime


image_link = 'quay.io/travisci/'
language_mapping = {
    'clojure': 'jvm',
    'scala': 'jvm',
    'groovy': 'jvm',
    'java': 'jvm',
    'elixir': 'erlang',
    'node_js': 'node-js'
}
languages = ['android', 'erlang', 'go', 'haskell', 'jvm', 'node-js', 'perl', 'php', 'python', 'ruby']


def get_travis_images():
    images = dict.fromkeys(languages, {})
    # Usage of images: images[<language>][<image_tag>] = 'provisioned_str'
    # For example,     images['jvm']['latest'] = 'Thu Feb  5 15:09:33 UTC 2015'

    jvm_tags = {
        'latest': 'Thu Feb  5 15:09:33 UTC 2015',
        'latest-2014-12-18_20-45-38': 'Fri Dec 12 23:29:11 UTC 2014',
        # Commented since it's actually the same as `latest`
        # 'latest-2015-02-11_15-09-23': 'Thu Feb  5 15:09:33 UTC 2015',
        'latest-2015-04-27_19-59-28': 'Mon Apr 27 15:14:25 UTC 2015'
        # Commented since it's actually the same as `latest`
        # 'latest-2015-04-28_13-48-40': 'Thu Feb  5 15:09:33 UTC 2015',
    }

    python_tags = {
        'latest': 'Thu Feb  5 15:09:33 UTC 2015',
        'latest-2015-04-27_20-07-07': 'Mon Apr 27 15:53:22 UTC 2015',
        'latest-2015-02-03_15-35-19': 'Tue Feb  3 03:09:28 UTC 2015',
        'latest-2014-12-18_20-45-35': 'Sat Dec 13 00:10:36 UTC 2014'
        # Commented since it's actually the same as `latest`
        # 'latest-2015-02-05_19-57-39': 'Thu Feb  5 15:09:33 UTC 2015',
    }

    for tag in jvm_tags:
        images['jvm'][tag] = {'provisioned_str': jvm_tags[tag]}
        if '-' in tag:
            images['jvm'][tag]['datetime'] = get_datetime_from_tag(tag)

    for tag in python_tags:
        images['python'][tag] = {'provisioned_str': python_tags[tag]}
        if '-' in tag:
            images['python'][tag]['datetime'] = get_datetime_from_tag(tag)

    # No longer using dev images because Travis did not use dev images to run jobs.
    # dev_images_names = ['dev-2015-04-27_15-16-43',
    #                     'dev-2015-04-14_14-07-53',
    #                     'dev-2015-04-09_05-23-50',
    #                     'dev-2015-04-09_04-17-38',
    #                     'dev-2015-04-07_15-33-12',
    #                     'dev-2014-12-09_17-21-14',
    #                     'dev-2014-09-28_15-22-30',
    #                     'dev-2015-02-05_15-27-38',
    #                     'dev-2014-12-12_23-30-37',
    #                     'dev-2015-02-03_03-27-47',
    #                     'dev-2014-11-15_17-27-27',
    #                     'dev-2014-11-15_17-58-04',
    #                     'dev-2014-12-04_20-19-37',
    #                     'dev-2014-11-04_16-14-00']
    # 'dev-2014-09-21_20-03-16', this image doesnt work, excluded
    # dev_images = {}
    # for i in dev_images_names:
    #     dev, year, month, day_hr, minute, sec = i.split('-')
    #     day = day_hr.split('_')[0]
    #     dt = datetime.datetime(int(year), int(month), int(day))
    #     dev_images[i] = dt
    return images


def get_datetime_from_tag(tag):
    latest, year, month, day_hr, minute, sec = tag.split('-')
    day = day_hr.split('_')[0]
    return datetime.datetime(int(year), int(month), int(day))
