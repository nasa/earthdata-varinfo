#!/bin/bash
###############################################################################
#
# A bash script to extract only the notes related to the most recent version of
# earthdata-varinfo from CHANGELOG.md
#
# 2023-06-16: Created
#
###############################################################################

CHANGELOG_FILE="CHANGELOG.md"
VERSION_PATTERN="^## v"
# Count number of versions in version file:
number_of_versions=$(grep -c "${VERSION_PATTERN}" ${CHANGELOG_FILE})

if [ ${number_of_versions} -gt 1 ]
then
	grep -B 9999 -m 2 "${VERSION_PATTERN}" ${CHANGELOG_FILE} | sed '$d' | sed '$d'
else
	cat ${CHANGELOG_FILE}
fi
