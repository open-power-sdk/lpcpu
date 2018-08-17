#!/bin/bash

# create a tarball with version file

HOME_DIR=`dirname $0`

TMP_DIR="lpcpu"

CURRENT_YEAR=`date +%Y`

function git_error
{
    echo -e "\nERROR: ${1}" 1>&2
    exit 1
}

function file_add
{
    echo -e "\nAdding ${1} to the base directory"
}

function msg
{
    echo -e "\n${1}"
}

# ${1} = directory to search
# ${2} = file/directory to search for
# ${3} = copy destination
function do_copy
{
    mkdir -p ${3}
    find ${1} -name ${2} -print0 | xargs -I '{}' -0 cp -av '{}' ${3}
}


msg "Create LPCPU Distribution Tarball"

pushd ${HOME_DIR} > /dev/null

lpcpu_version=`git show -s --pretty=format:"%H %ci"`

msg "Creating clean base directory"
if [ -e "${TMP_DIR}" ]; then
    rm -Rf ${TMP_DIR}
fi
mkdir ${TMP_DIR}

msg "Recording versions"
echo "1: ${lpcpu_version}" | tee ${TMP_DIR}/version

file_add "lpcpu.sh"
cp -v lpcpu.sh ${TMP_DIR}

msg "Updating lpcpu.sh"
sed -i -e "s/VERSION_STRING=\"\"/VERSION_STRING=\"$lpcpu_version\"/" ${TMP_DIR}/lpcpu.sh

file_add "README"
cp -v README ${TMP_DIR}

file_add "LICENSE.TXT (Eclipse Public License)"
cp -v LICENSE.TXT ${TMP_DIR}

file_add "rtst.py"
cp -v rtst.py ${TMP_DIR}

file_add "README.rtst"
cp -v README.rtst ${TMP_DIR}

file_add "tools"
cp -av tools ${TMP_DIR}

file_add "postprocess"
cp -av postprocess ${TMP_DIR}

file_add "perl"
cp -av perl ${TMP_DIR}

cp download-jschart-dependencies.sh ${TMP_DIR}

# finish up
msg "Creating tarball:"
tar cjvf lpcpu.tar.bz2 lpcpu

popd > /dev/null
