import queue

from .utils import TupleSortingOn0, to_percent


def is_job_bb(l):
    t = l['orig']
    if '.bb.' in t['tr_using_worker']:
        return True
    return False


def is_job_gce(l):
    t = l['orig']
    if 'gce' in t['tr_worker_instance']:
        return True
    return False


def is_job_image_same(l):
    t = l['orig']
    if t['tr_build_image'] != 'NA':
        if l['tr_build_image'] == t['tr_build_image']:
            return True
    return False


def is_job_bb_new(t):
    if '.bb.' in t['tr_using_worker']:
        return True
    return False


def is_job_gce_new(t):
    if 'gce' in t['tr_worker_instance']:
        return True
    return False


def is_job_image_same_new(l, t):
    if t['tr_build_image'] != 'NA':
        if l['tr_build_image'] == t['tr_build_image']:
            return True
    return False


# Project-based match rate tells us how many project have all matching jobs and how many project have all mismatching
# jobs so we can deduce whether matching depends significantly on project.
# argument: mismatch - list of tr_job_id that mismatched
def project_based_match_rate(projects, local_javas):
    print('\n--------------project-based match rate--------------')
    print('\nbuilds visualization:\n')
    print('build labels:')
    print('\t0: mismatch\n\t1: match\n\t2:  mix of match and mismatch')
    print('\t3: mix of reproduced and not reproduced')
    print('\t4: not reproduced')
    print('tags:')
    print('\t*: image_diff')
    print('\t^: was originally BB build')
    print('\tG: was originally GCE build')
    print('\tS: used the same image\n')

    for l in local_javas:
        for p in projects:
            for b in projects[p]:
                if l['tr_job_id'] in projects[p][b]:
                    projects[p][b][l['tr_job_id']] = l

    # Stats.
    total_mixed_matching = 0
    total_mixed_matching_image_diff = 0

    #######
    p_all_match = 0
    p_all_mismatch = 0
    p_all_not_reproduced = 0
    total_builds = 0

    total_builds_with_all_jobs_match = 0
    total_builds_with_all_jobs_mismatch = 0
    total_builds_with_all_jobs_not_reproduced = 0

    total_jobs = 0
    total_jobs_mismatch = 0
    pq_for_projects = queue.PriorityQueue()
    for p in projects:
        builds_with_all_jobs_mismatch = 0
        builds_with_all_jobs_not_reproduced = 0
        builds_with_all_jobs_match = 0
        num_builds_in_project = len(projects[p])
        p_name = p
        if len(p) > 20:
            p_name = p[:20]
        line = '{0: <20}'.format(p_name) + ' : '
        pq_for_builds = queue.PriorityQueue()
        for b in projects[p]:
            total_builds += 1
            num_of_job_in_build = len(projects[p][b])
            m_mm_u = [0, 0, 0]
            build_label = 0
            tag = ' '
            for job in projects[p][b]:
                total_jobs += 1
                if projects[p][b][job] == -1:  # Not reproduced.
                    matching_status = -1
                else:
                    matching_status = int(projects[p][b][job]['match'])
                if matching_status == 1:
                    m_mm_u[0] += 1
                elif matching_status == 0:
                    m_mm_u[1] += 1
                elif matching_status == -1:
                    m_mm_u[2] += 1

                if matching_status != -1:
                    if is_job_image_same(projects[p][b][job]):
                        tag = 'S'
                    else:
                        tag = '*'
                    if is_job_bb(projects[p][b][job]):
                        tag = '^'
                    if is_job_gce(projects[p][b][job]):
                        tag = 'G'

                # if p == 'HubSpot/Singularity' and tag == '*':
                #     print (projects[p][b][job]['job_link'])

            total_jobs_mismatch += m_mm_u[1]

            # Error checking.
            if sum(m_mm_u) != num_of_job_in_build:
                print('ERROR ! sum(m_mm_u) != num_of_job_in_build!')

            # Check for mixing.
            # Mixing of reproduced and not_reproduced.
            if m_mm_u[2] != 0 and (m_mm_u[0] != 0 or m_mm_u[1] != 0):
                print('found mixing of reproduced and not_reproduced')
                build_label = 3
            if m_mm_u[0] != 0 and m_mm_u[1] != 0:
                # print('found mixing of match and mismatch')
                build_label = 2
            if m_mm_u[0] == num_of_job_in_build:  # Build match.
                builds_with_all_jobs_match += 1
                build_label = 1
            if m_mm_u[1] == num_of_job_in_build:
                builds_with_all_jobs_mismatch += 1
                build_label = 0
            if m_mm_u[2] == num_of_job_in_build:
                builds_with_all_jobs_not_reproduced += 1
                build_label = 4  # not_reproduced

            # Tags.
            build_print = str(build_label) + tag + ' '
            pq_for_builds.put(TupleSortingOn0((int(b), build_print)))

            # Stats.
            if build_label == 2:
                total_mixed_matching += 1
                if tag != 'S':
                    total_mixed_matching_image_diff += 1

        while not pq_for_builds.empty():
            pri, build_print = pq_for_builds.get()
            line += build_print

        pq_for_projects.put(TupleSortingOn0((len(projects[p]), line)))

        total_builds_with_all_jobs_match += builds_with_all_jobs_match
        total_builds_with_all_jobs_mismatch += builds_with_all_jobs_mismatch
        total_builds_with_all_jobs_not_reproduced += builds_with_all_jobs_not_reproduced

        if builds_with_all_jobs_match == num_builds_in_project:
            p_all_match += 1
        if builds_with_all_jobs_mismatch == num_builds_in_project:
            p_all_mismatch += 1
        if builds_with_all_jobs_not_reproduced == num_builds_in_project:
            p_all_not_reproduced += 1

    while not pq_for_projects.empty():
        pri, line = pq_for_projects.get()
        print(line)

    print('\n----------------------------------------------------')
    print('len(projects) = ', len(projects))
    print('p_all_match = ', p_all_match)
    print('p_all_mismatch = ', p_all_mismatch)
    print('p_all_not_reproduced = ', p_all_not_reproduced)
    print('total_builds_with_all_jobs_match = ', total_builds_with_all_jobs_match)
    print('total_builds_with_all_jobs_mismatch = ', total_builds_with_all_jobs_mismatch)
    print('total_builds_with_all_jobs_not_reproduced = ', total_builds_with_all_jobs_not_reproduced)
    pr_job_mismatch = float(total_jobs_mismatch) / float(total_jobs)
    print('P(job_mismatch) = ', pr_job_mismatch)
    pr_build_mismatch = float(total_builds_with_all_jobs_mismatch) / float(total_builds)
    print('P(build_mismatch) = ', pr_build_mismatch)
    print('P(build_all_jobs_mismatch | job_mismatch) = ', to_percent(pr_build_mismatch / pr_job_mismatch))
    print('out of all builds with mixed_matching), how many are image diff = ',
          to_percent(total_mixed_matching_image_diff / total_mixed_matching))
    print('----------------------------------------------------\n\n\n')


# Project-based match rate tells us how many project have all matching jobs and how many project have all mismatching
# jobs so we can deduce whether matching depends significantly on project.
# argument: mismatch - list of tr_job_id that mismatched
def project_based_match_rate_new(pairs):
    print('\n--------------project-based match rate--------------')
    print('\nbuilds visualization:\n')
    print('build labels:')
    print('\t0: mismatch\n\t1: match\n\t2: mix of match and mismatch')
    print('\t3: mix of reproduced and not reproduced')
    print('\t4: not reproduced')
    print('tags:')
    print('\t*: image_diff')
    print('\t^: was originally BB build')
    print('\tG: was originally GCE build')
    print('\tS: used the same image\n')

    projects = {}
    for p in pairs:
        repo = p['repo']
        if repo not in projects:
            projects[repo] = []
        projects[repo].append(p['failed_build']['jobs'])
        projects[repo].append(p['passed_build']['jobs'])

    # Stats.
    total_mixed_matching = 0
    total_mixed_matching_image_diff = 0

    #######
    p_all_match = 0
    p_all_mismatch = 0
    p_all_not_reproduced = 0
    total_builds = 0

    total_builds_with_all_jobs_match = 0
    total_builds_with_all_jobs_mismatch = 0
    total_builds_with_all_jobs_not_reproduced = 0

    total_jobs = 0
    total_jobs_mismatch = 0
    pq_for_projects = queue.PriorityQueue()
    for p in projects:
        builds_with_all_jobs_mismatch = 0
        builds_with_all_jobs_not_reproduced = 0
        builds_with_all_jobs_match = 0
        num_builds_in_project = len(projects[p])
        p_name = p
        if len(p) > 20:
            p_name = p[:20]
        line = '{0: <20}'.format(p_name) + ' : '
        pq_for_builds = queue.PriorityQueue()

        build_count = 0
        for b in projects[p]:
            build_count += 1
            total_builds += 1
            num_of_job_in_build = len(b)
            m_mm_u = [0, 0, 0]
            build_label = 0
            tag = '-'
            for job in b:
                total_jobs += 1
                if 'match' in job:
                    matching_status = int(job['match'])
                else:
                    matching_status = -1
                if matching_status == 1:
                    m_mm_u[0] += 1
                elif matching_status == 0:
                    m_mm_u[1] += 1
                elif matching_status == -1:
                    m_mm_u[2] += 1

                if matching_status != -1:
                    if is_job_image_same_new(job['reproduced_result'], job['orig_result']):
                        tag = 'S'
                    else:
                        tag = '*'
                    if is_job_bb_new(job['orig_result']):
                        tag = '^'
                    if is_job_gce_new(job['orig_result']):
                        tag = 'G'

                # if p == 'HubSpot/Singularity' and tag == '*':
                #     print (projects[p][b][job]['job_link'])

            total_jobs_mismatch += m_mm_u[1]

            # Error checking.
            if sum(m_mm_u) != num_of_job_in_build:
                print('ERROR ! sum(m_mm_u) != num_of_job_in_build!')

            # Check for mixing.
            # Mixing of reproduced and not_reproduced.
            if m_mm_u[2] != 0 and (m_mm_u[0] != 0 or m_mm_u[1] != 0):
                # print('found mixing of reproduced and not_reproduced')
                build_label = 3
            if m_mm_u[0] != 0 and m_mm_u[1] != 0:
                # print('found mixing of match and mismatch')
                build_label = 2
            if m_mm_u[0] == num_of_job_in_build:  # Build match.
                builds_with_all_jobs_match += 1
                build_label = 1
            if m_mm_u[1] == num_of_job_in_build:
                builds_with_all_jobs_mismatch += 1
                build_label = 0
            if m_mm_u[2] == num_of_job_in_build:
                builds_with_all_jobs_not_reproduced += 1
                build_label = 4  # not_reproduced

            # Tags.
            build_print = str(build_label) + tag + ' '
            pq_for_builds.put(TupleSortingOn0((int(build_count), build_print)))

            # Stats.
            if build_label == 2:
                total_mixed_matching += 1
                if tag != 'S':
                    total_mixed_matching_image_diff += 1

        while not pq_for_builds.empty():
            pri, build_print = pq_for_builds.get()
            line += build_print

        pq_for_projects.put(TupleSortingOn0((len(projects[p]), line)))

        total_builds_with_all_jobs_match += builds_with_all_jobs_match
        total_builds_with_all_jobs_mismatch += builds_with_all_jobs_mismatch
        total_builds_with_all_jobs_not_reproduced += builds_with_all_jobs_not_reproduced

        if builds_with_all_jobs_match == num_builds_in_project:
            p_all_match += 1
        if builds_with_all_jobs_mismatch == num_builds_in_project:
            p_all_mismatch += 1
        if builds_with_all_jobs_not_reproduced == num_builds_in_project:
            p_all_not_reproduced += 1

    while not pq_for_projects.empty():
        pri, line = pq_for_projects.get()
        print(line)

    print('\n----------------------------------------------------')
    print('len(projects) = ', len(projects))
    print('p_all_match = ', p_all_match)
    print('p_all_mismatch = ', p_all_mismatch)
    print('p_all_not_reproduced = ', p_all_not_reproduced)
    print('total_builds_with_all_jobs_match = ', total_builds_with_all_jobs_match)
    print('total_builds_with_all_jobs_mismatch = ', total_builds_with_all_jobs_mismatch)
    print('total_builds_with_all_jobs_not_reproduced = ', total_builds_with_all_jobs_not_reproduced)
    pr_job_mismatch = float(total_jobs_mismatch) / float(total_jobs)
    print('P(job_mismatch) = ', pr_job_mismatch)
    pr_build_mismatch = float(total_builds_with_all_jobs_mismatch) / float(total_builds)
    print('P(build_mismatch) = ', pr_build_mismatch)
    print('P(build_all_jobs_mismatch | job_mismatch) = ', to_percent(pr_build_mismatch / pr_job_mismatch))
    print('out of all builds with mixed_matching), how many are image diff = ',
          to_percent(total_mixed_matching_image_diff / total_mixed_matching))
    print('----------------------------------------------------\n\n\n')


def add_att_to_results(csv_data, local_javas):
    print('\n----------------adding att to results---------------')
    # Add datetime attribute.
    for l in local_javas:
        found_in_csv_data = [d for d in csv_data if d['tr_job_id'] == str(l['tr_job_id'])]
        if not found_in_csv_data:
            # print(l['tr_job_id'] , 'not found in CSV DATA!')
            l['datetime'] = 'NA'
            l['job_link'] = 'NA'
            continue
        d = found_in_csv_data[0]
        if 'gh_build_started_at' not in d:
            print(d)
        time = d['gh_build_started_at']
        l['datetime'] = time
        l['job_link'] = d['job_link']


# Yearly match rate analysis. Calculate match rate for jobs categorized by year. Also prints how many Blue Box jobs and
# Trusty jobs by year.
def yearly_match_rate(local_javas):
    print('--------------yearly based match rate---------------')
    # Print header.
    print('year|match|out_of| rate|   BB |  GCE |TRUSTY|has_dt')
    total_has_dt = 0
    total_has_dt_match = 0
    total_no_dt = 0
    total_no_dt_match = 0

    for y in range(2011, 2017):
        jobs_in_year = [l for l in local_javas if str(y) in l['datetime']]
        mismatch_in_year = [l for l in jobs_in_year if not l['match']]
        matched_count = len(jobs_in_year) - len(mismatch_in_year)
        bb_in_year = 0
        trusty_in_year = 0
        gce_in_year = 0
        has_dt = 0
        for l in jobs_in_year:
            t = l['orig']
            if '.bb.' in t['tr_using_worker']:
                bb_in_year += 1
            if is_job_gce(l):
                gce_in_year += 1
            if 'trusty' in t['tr_os']:
                trusty_in_year += 1
            if t['tr_build_image'] != 'NA':
                has_dt += 1
                total_has_dt += 1
                total_has_dt_match += l['match']
            else:
                total_no_dt += 1
                total_no_dt_match += l['match']
        if jobs_in_year:
            print(y,
                  '{0:5}'.format(matched_count),
                  '{0:6}'.format(len(jobs_in_year)),
                  '{0:>5}'.format(to_percent(float(matched_count) / float(len(jobs_in_year)))),
                  '{0:6}'.format(bb_in_year),
                  '{0:6}'.format(gce_in_year),
                  '{0:6}'.format(trusty_in_year),
                  '{0:6}'.format(has_dt))

    print('total jobs WITH provisioning datetime:', total_has_dt, ' Pr(match | has_dt) =',
          to_percent(total_has_dt_match / float(total_has_dt)))
    print('total jobs WITHOUT provisioning datetime:', total_no_dt, ' Pr(match | no_dt)=',
          to_percent(total_no_dt_match / float(total_no_dt)))


def redo_2015_2016_jobs(local_javas):
    redo = []
    for l in local_javas:
        time = l['datetime']
        if '2015' in time or '2016' in time:
            redo.append('')
    for r in redo:
        print(r)


def find_latest_use_of_quay_image(local_javas):
    latest_quay_use = []
    for l in local_javas:
        t = l['orig']
        if 'Thu Feb  5 15:09:33 UTC 2015' in t['tr_build_image'] and '2016' in l['datetime']:
            latest_quay_use.append(l['datetime'] + l['job_link'])
    print('latest_quay_use')
    for l in latest_quay_use:
        print(l)


# Helper function for the status match rate matrix analysis.
def init_matrix_for_status_analysis(status):
    m = {}
    for s in status:
        tmp = {}
        for ss in status:
            tmp[ss] = 0
        m[s] = tmp
    return m


# Calculate and print status match rate matrix.
def status_match_rate_matrix(local_javas, status, only_same_image_jobs):
    print('--------------status match rate matrix--------------')
    print('only_same_image_jobs = ', only_same_image_jobs)
    m = init_matrix_for_status_analysis(status)
    for l in local_javas:
        t = l['orig']
        if only_same_image_jobs:
            if l['tr_build_image'] == t['tr_build_image'] and l['tr_build_image'] != 'NA':
                m[t['tr_log_status']][l['tr_log_status']] += 1
        else:
            m[t['tr_log_status']][l['tr_log_status']] += 1

    mm = init_matrix_for_status_analysis(status)

    status_count = {}

    for t_status in m:
        count = 0
        for l_status in m[t_status]:
            count += m[t_status][l_status]
        for l_status in mm[t_status]:
            mm[t_status][l_status] = count
        status_count[t_status] = count

    for t_status in m:
        for l_status in m[t_status]:
            if mm[t_status][l_status] != 0:
                mm[t_status][l_status] = m[t_status][l_status] / float(mm[t_status][l_status])

    # Printing matrix.
    # Print header.
    line = '           '
    for s in status:
        line += ('{0: <10}'.format(s) + ' ')
    print(line)
    # Print count for category.
    line = '           '
    for s in status:
        line += ('{0: <10}'.format(status_count[s]) + ' ')
    print(line)

    for s in status:
        line = '{0: <10}'.format(s) + ' '
        for ss in status:
            # line+='{:4}'.format(mm[t_status][l_status])
            # line += ('%6.f' %mm[t_status][l_status])
            line += ('{0:.8f}'.format(mm[ss][s]) + ' ')
        print(line)
    print('')


# For jobs that have matching log_status but still mismatch, accumulate the mismatching attributes.
def matched_status_but_mismatch_analysis(att_acc, l, t):
    atts_to_skip = [
        'tr_log_testduration',
        'tr_log_buildduration',
        'tr_log_setup_time',
        'tr_err_msg',
        'tr_build_image',
        'tr_worker_instance',
        'tr_connection_lines',
        'tr_using_worker',
        'could_not_resolve_dep',
        'tr_os',
        'tr_cookbook',
    ]

    for att in t:
        att_match = 1
        if att == 'tr_log_tests_failed':
            if set(l[att]) != set(t[att]):
                att_match = 0
        else:
            if att not in atts_to_skip:
                if l[att] != t[att]:
                    att_match = 0

        if not att_match:
            if att not in att_acc:
                att_acc[att] = 1
            else:
                att_acc[att] += 1


def which_builds_have_all_matching_jobs(local_javas, csv_data):
    print('\n---------------------------------------------')
    builds = {}
    build_ids = []
    for d in csv_data:
        build = d['tr_build_id']
        job = d['tr_job_id']
        if build not in builds:
            tmp = {
                job: -1,  # -1 to indicate 'not set yet,' as default.
            }
            builds[build] = tmp
        else:
            builds[build][job] = -1
        build_ids.append(build)

    for l in local_javas:
        if l['match']:
            for build in builds:
                if l['tr_job_id'] in builds[build]:
                    builds[build][l['tr_job_id']] = 1

    for l in local_javas:
        if not l['match']:
            for build in builds:
                if l['tr_job_id'] in builds[build]:
                    builds[build][l['tr_job_id']] = 0

    builds_with_all_jobs_matching = []
    builds_not_reproduced = []

    for build in builds:
        all_match = 1
        all_not_reproduced = 0
        for job in builds[build]:
            if builds[build][job] != 1:
                all_match = 0
            if builds[build][job] == -1:
                all_not_reproduced += 1

        if all_not_reproduced == len(builds[build]):
            builds_not_reproduced.append(build)

        if all_match:
            builds_with_all_jobs_matching.append(build)

    print('builds_with_all_jobs_matching: ', len(builds_with_all_jobs_matching))
    print('builds_not_reproduced: ', len(builds_not_reproduced))
    return set(build_ids), builds_with_all_jobs_matching


def get_pairs_all_matching(pairs, build_ids, builds_all_matching):
    pairs_all_matching = []
    total_pairs = 0
    for prev_b, b in pairs:
        if prev_b in builds_all_matching and b in builds_all_matching:
            pairs_all_matching.append((prev_b, b))
        if prev_b in build_ids and b in build_ids:
            total_pairs += 1
    print('pairs with both builds all matching = ', len(pairs_all_matching), 'out of', total_pairs, '=',
          to_percent(float(len(pairs_all_matching)) / total_pairs))
    return pairs_all_matching


def image_match_rate_analysis(local_javas):
    print('\n--------------image_match_rate_analysis-------------')
    print('of the jobs that have provisioning datetime:   (excluding GCE jobs)')
    image_diff = 0
    image_diff_match = 0
    image_same = 0
    image_same_match = 0

    to_print = []
    for l in local_javas:
        t = l['orig']
        # Image analysis.
        if t['tr_build_image'] != 'NA':
            if not is_job_gce(l):
                if l['tr_build_image'] != t['tr_build_image']:
                    image_diff += 1
                    if l['match']:
                        image_diff_match += 1
                else:
                    image_same += 1
                    if l['match']:
                        image_same_match += 1
                        to_print.append(l['tr_job_id'])

    print('image_same:', image_same, ' match', image_same_match, ' =', to_percent(image_same_match / float(image_same)))
    print('image_diff:', image_diff, ' match', image_diff_match, ' =', to_percent(image_diff_match / float(image_diff)))
    print('printing image_same but mis-match:')
    print(to_print)


def get_num_of_pr_jobs(local_javas, jobs_is_pr):
    is_pr = 0
    is_pr_match = 0
    for l in local_javas:
        if jobs_is_pr[l['tr_job_id']]:
            is_pr += 1
            if l['match']:
                is_pr_match += 1
    print('total jobs is_pr = ', is_pr,
          ' is_pr_match = ', is_pr_match,
          ' match rate =', to_percent(is_pr_match / float(is_pr)))


def get_num_of_gce_jobs(local_javas):
    worker_diff = 0
    gce = 0
    match = 0
    for l in local_javas:
        t = l['orig']
        # GCE jobs.
        if l['tr_worker_instance'] != t['tr_worker_instance']:
            worker_diff += 1
            if 'gce' in t['tr_worker_instance']:
                gce += 1
                match += l['match']
    print('total GCE jobs = ', gce,
          ', this should equal worker_diff = ', worker_diff,
          ' match rate =', to_percent(match / float(gce)))


def get_num_of_trusty_jobs(local_javas):
    trusty = 0
    match = 0
    for l in local_javas:
        t = l['orig']
        if t['tr_os'] == 'trusty':
            trusty += 1
            match += l['match']
            if 'gce' not in t['tr_worker_instance']:
                print('TRUSTY but NOT ON GCE!')
                print(t['tr_job_id'])
                raise Exception
    print('total TRUSTY jobs = ', trusty, '  match rate =', to_percent(match / float(trusty)))


def get_num_of_bb_jobs(local_javas):
    bb = 0
    bb_with_dt = 0
    match = 0
    for l in local_javas:
        t = l['orig']
        if '.bb.' in t['tr_using_worker']:
            bb += 1
            match += l['match']
            if t['tr_build_image'] != 'NA':
                bb_with_dt += 1
    print('total BB jobs = ', bb, '  BB_with_provisioning_datetime = ', bb_with_dt,
          ' match rate =', to_percent(match / float(bb)))


# Matched log status but still mismatch_analysis.
def matched_status_but_still_mismatch_att_acc(local_javas):
    print('\n------matched log status, but still mis-match-------')
    print('mis-match att:')
    att_acc_for_status_all = {}
    att_acc_for_status_ok_ok = {}
    att_acc_for_status_broken_broken = {}
    all_pair_count = 0
    okok_pair_count = 0
    brokenbroken_pair_count = 0
    ids_to_print = []  # For debug purposes.
    for l in local_javas:
        t = l['orig']
        if l['tr_log_status'] == t['tr_log_status'] and not l['match']:
            matched_status_but_mismatch_analysis(att_acc_for_status_all, l, t)
            all_pair_count += 1
            if t['tr_log_status'] == 'ok':
                matched_status_but_mismatch_analysis(att_acc_for_status_ok_ok, l, t)
                okok_pair_count += 1
                ids_to_print.append(l['tr_job_id'])
            if t['tr_log_status'] == 'broken':
                matched_status_but_mismatch_analysis(att_acc_for_status_broken_broken, l, t)
                brokenbroken_pair_count += 1
    print('all matching status pairs:    jobs count = ', all_pair_count)
    print('---------------------------')
    print_dict_pq(att_acc_for_status_all)
    print('')
    print('ok-ok:     jobs count = ', okok_pair_count)
    print('---------------------------')
    print_dict_pq(att_acc_for_status_ok_ok)
    print('')
    print('broken-broken:     jobs count = ', brokenbroken_pair_count)
    print('---------------------------')
    print_dict_pq(att_acc_for_status_broken_broken)
    print('')
    print('ok, ok but still mismatch: ', ids_to_print)


def print_dict_pq(d):
    pq = queue.PriorityQueue()
    for k in d:
        line = k + '  ' + str(d[k])
        pq.put(TupleSortingOn0((-d[k], line)))
    while not pq.empty():
        pri, line = pq.get()
        print(line)


def connection_lines_analytics(local_javas):
    print('\n-------------connection lines analytics--------------')
    terms_to_catch = ['getRepositorySession()', "Can't get http", '404 Not Found', 'Failed to fetch', 'MockWebServer',
                      'ssl.SSL', 'Received request:', 'Unauthorized.', 'Failed to connect', 'Connection refused',
                      'SocketTimeOut', 'failed to upload', 'the requested URL returned error', 'unknown host']
    print('terms to catch:')
    for t in terms_to_catch:
        print(t)
    print('\n')
    jobs_with_connection_line = 0
    jobs_with_connection_line_mismatch = 0
    for l in local_javas:
        if len(l['tr_connection_lines']) > 1:
            jobs_with_connection_line += 1
            if not l['match']:
                jobs_with_connection_line_mismatch += 1

    total_match = 0
    total_mismatchmm = 0
    total_match_hc = 0
    total_mismatch_hc = 0

    image_same = 0
    image_diff = 0
    image_same_hc = 0
    image_diff_hc = 0

    image_same_mismatch = 0
    image_diff_mismatch = 0
    image_same_mismatch_hc = 0
    image_diff_mismatch_hc = 0

    has_dt = 0
    no_dt = 0
    has_dt_hc = 0
    no_dt_hc = 0

    for l in local_javas:
        t = l['orig']
        hc = len(l['tr_connection_lines']) > 1

        # print(l['match'])
        if l['match'] == 1:
            total_match += 1
            if hc:
                total_match_hc += 1
        else:
            total_mismatchmm += 1
            if hc:
                total_mismatch_hc += 1

        # NON-GCE JOBS - Find missing images.
        if l['tr_worker_instance'] == t['tr_worker_instance']:
            # Log has provisioning datetime.
            if t['tr_build_image'] != 'NA':
                has_dt += 1
                if hc:
                    has_dt_hc += 1

                if l['tr_build_image'] == t['tr_build_image']:
                    image_same += 1
                    if hc:
                        image_same_hc += 1

                    if not l['match']:
                        image_same_mismatch += 1
                        if hc:
                            image_same_mismatch_hc += 1
                else:
                    image_diff += 1
                    if hc:
                        image_diff_hc += 1

                    if not l['match']:
                        image_diff_mismatch += 1
                        if hc:
                            image_diff_mismatch_hc += 1
            else:
                no_dt += 1
                if hc:
                    no_dt_hc += 1

    # print('out of total_match, has_connection_lines =', to_percent(float(total_match_hc)/total_match))
    # print(total_mismatch_hc,
    #       total_mismatchmm,
    #       'out of total_mismatch, has_connection_lines =', to_percent(float(total_mismatch_hc) / total_mismatchmm))
    print('out of total_image_same, has_connection_lines =', to_percent(float(image_same_hc) / image_same))
    print('out of total_image_diff, has_connection_lines =', to_percent(float(image_diff_hc) / image_diff))
    print('out of total_image_same_and_mismatch, has_connection_lines =',
          to_percent(float(image_same_mismatch_hc) / image_same_mismatch))
    print('out of total_image_diff_and_mismatch, has_connection_lines =',
          to_percent(float(image_diff_mismatch_hc) / image_diff_mismatch))
    print('out of total_has_dt, has_connection_lines =', to_percent(float(has_dt_hc) / has_dt))
    print('out of total_no_dt, has_connection_lines =', to_percent(float(no_dt_hc) / no_dt))

    print('Pr(has_connection_line | match) =', to_percent(0))
    print('Pr(has_connection_line | mismatch) =', to_percent(0))
    print('Pr(has_connection_line | has_dt) =', to_percent(0))
    print('Pr(has_connection_line | no_dt) =', to_percent(0))
    print('Pr(has_connection_line | image_same) =', to_percent(0))
    print('Pr(has_connection_line | image_diff) =', to_percent(0))
    print('Pr(has_connection_line | image_same_and_mismatch) =', to_percent(0))
    print('Pr(has_connection_line | image_diff_and_mismatch) =', to_percent(0))

    print('jobs with connection lines =', jobs_with_connection_line,
          ' of these, mismatch =', jobs_with_connection_line_mismatch,
          to_percent(jobs_with_connection_line_mismatch / float(jobs_with_connection_line)))


# Finds images with differnet datetime (meaning we did not reproduce with the same image). Then checks if that job was
# originally run on BB to confirm that all the missing images were BB images.
def find_missing_images(local_javas):
    print('\n---------------find missing images-----------------')
    image_error = 0
    image_missing = []

    missing_images = [
        'Wed Apr  8 13:53:33 UTC 2015',
        'Sat Apr 25 03:08:46 UTC 2015',
        'Wed Feb  4 18:22:50 UTC 2015',
        'Sun Dec  7 05:49:51 UTC 2014'
    ]
    jobs_of_missing_images = []

    bb = 0

    quay = ['Thu Feb  5 15:09:33 UTC 2015', 'Fri Dec 12 23:29:11 UTC 2014', 'Mon Apr 27 15:14:25 UTC 2015']
    for l in local_javas:
        t = l['orig']
        # NON-GCE JOBS - find missing images
        if l['tr_worker_instance'] == t['tr_worker_instance']:
            # log has provisioning datetime
            if t['tr_build_image'] != 'NA':
                if l['tr_build_image'] != t['tr_build_image']:

                    image_missing.append(t['tr_build_image'])

                    if t['tr_build_image'] in quay:
                        image_error += 1
                        # print (l['tr_job_id'])
                        # raise Exception

                    if t['tr_build_image'] in missing_images:
                        jobs_of_missing_images.append(l['tr_job_id'])
                        if '.bb.' in t['tr_using_worker']:
                            bb += 1

    print('excluding GCE Jobs:')
    print('image_missing = ', set(image_missing) - set(quay))
    print('image_error (datetime is Quay, why mapped different? )  = ', image_error)
    print('jobs of missing images:', jobs_of_missing_images)
    print('len(jobs of missing images) = ', len(jobs_of_missing_images), 'of these, bb =', bb)


def find_missing_cookbook(local_javas):
    local_cookbooks = [l['tr_cookbook'] for l in local_javas]
    bb_cookbooks = [l['orig']['tr_cookbook'] for l in local_javas if is_job_bb(l)]
    all_orig_cookbooks = [l['orig']['tr_cookbook'] for l in local_javas]
    print(set(local_cookbooks))
    print(set(bb_cookbooks))
    print(set(all_orig_cookbooks))


def print_pairs_status(pairs):
    total_matching_pairs = 0
    total_pair_with_jobs_skipped = 0
    for p in pairs:
        print(p['repo'] + '/' + p['pr_num'] + '-' + p['failed_build']['build_id'] + '-' + p['passed_build']['build_id'])
        builds = [p['failed_build'], p['passed_build']]
        pair_match = 1
        pair_jobs_skipped = 0
        for i in range(2):
            if i == 0:
                print('\tfailed build:')
            else:
                print('\tpassed build:')

            for job in builds[i]['jobs']:
                job_id = str(job['job_id'])
                job_print = ['\t\t' + job_id]
                if 'reproduced_result' in job:
                    job_print.append('reproduced')
                    if job['match']:
                        job_print.append('matched')
                    else:
                        job_print.append('mismatched')
                        pair_match = 0
                else:
                    pair_match = 0
                    pair_jobs_skipped = 1

                print(' '.join(job_print))

                if 'reproduced_result' in job and not job['match']:
                    print('\t\tmismatch atts:')
                    try:
                        for m in job['mismatch_atts']:
                            print('\t\t' + m)
                    except UnicodeEncodeError:
                        print('\t\tUnicodeEncodeError when printing mismatch atts\n')

        total_matching_pairs += pair_match
        total_pair_with_jobs_skipped += pair_jobs_skipped
    print('matching pairs =', total_matching_pairs, '  total_pair_with_jobs_skipped =', total_pair_with_jobs_skipped)
