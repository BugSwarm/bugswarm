"""
String constants for each reason that Pair Filter filters a pair. Also used in the evaluation script.

Think carefully before changing these constants! Any changes will create inconsistency in the 'filtered_reason'
attribute in the metadata database. In turn, changes will break the evaluation script. In short, if these constants
change, then to remove inconsistencies between previously created artifacts and newly created artifacts, either every
artifact will need to be recreated or the metadata database will need to be updated so that previously created artifacts
use the new constants in their metadata.
"""

NO_HEAD_SHA = 'no head sha'
NO_ORIGINAL_LOG = 'do not have original log'
ERROR_READING_ORIGINAL_LOG = 'error when reading original log'
NO_IMAGE_PROVISION_TIMESTAMP = 'original log does not have provisioned datetime string'
INACCESSIBLE_IMAGE = 'do not have image'
NOT_RESETTABLE = 'not resettable'  # Deprecated.
NOT_ACQUIRABLE = 'not acquirable'  # Deprecated.
NOT_AVAILABLE = 'not available'
SAME_COMMIT_PAIR = 'failed build has same sha with passed build'
