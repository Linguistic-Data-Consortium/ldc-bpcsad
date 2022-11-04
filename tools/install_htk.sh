#!/bin/bash
# Install HTK.
set -e


# Avoid issues with availability of realpath on OS X and POSIX compliance of
# readlink. Admittedly heavyweight, but Python is already a requirement, so call it a day.
function get_abspath () {
    python3 -c "from pathlib import Path; print(Path('${1}').resolve())"
    return 0
}


# Absolute path to third-party tools directory.
TOOLS_DIR=$(dirname $(get_abspath $0))

# Command line help message.
USAGE="usage: install_htk.sh [--help] [--njobs JOBS] [--prefix STAGE] [--stage STAGE] tar-file

Install HTK tools.

arguments:
  tar-file   Path to downloaded HTK tarball.

optional arguments:
  --help     Show this message and exit.
  --njobs    Build HTK using JOBS parallel jobs. (Default: 4)
  --prefix   Install HTK tools to PREFIX/bin. (Default: /usr/local)
  --stage    Run install script starting at stage STAGE. (Default: 1)"

  
#######################
# Command line options
#######################
njobs=4  # Number of parallel jobs.
prefix=/usr/local  # Installation prefix.
stage=1  # Stage to begin from.
htk_tar=
while true; do
    # No arguments.
    [ -z "${1:-}" ] && break;
    case "$1" in
	--help)
	  echo "$USAGE"
	  exit 0 ;;
	--njobs)
       	  njobs=$2;
	  shift 2;
	  ;;
        --prefix)
	  prefix=$2;
	  shift 2;
	  ;;
	--stage)
	  stage=$2;
	  shift 2;
	  ;;
        *) break;
    esac
done
if [ $# != 1 ]; then
    echo "$USAGE"
    exit 1;
fi
htk_tar=$1
prefix=$(get_abspath ${prefix})


#######################
# Verify HTK
#######################
htk_dir=${TOOLS_DIR}/htk
if [ $stage -le 1 ]; then
    rm -fr $htk_dir
    echo "$0: Untarring HTK to ${htk_dir}..."
    tar -xf $htk_tar -C $TOOLS_DIR

    echo "$0: Verifying your HTK version..."
    if [ -z "$(head -n 1 ${htk_dir}/README | grep 3.4.1)" ]; then
	echo "$0: Wrong version of HTK found. Please download HTK 3.4.1 and re-run:"
	echo "$0:"
	echo "$0:     https://htk.eng.cam.ac.uk/download.shtml"
	exit 1
    fi
fi


#######################
# Build HTK
#######################
htk_patch=${TOOLS_DIR}/htk_patch.txt
if [ $stage -le 2 ]; then
    cd $htk_dir

    if [ ! -f patch.succeeded ]; then
	echo "$0: Patching HTK..."
	patch -p1 < $htk_patch
	touch patch.succeeded
    fi

    echo "$0: Configuring HTK for your system..."
    ./configure --prefix $prefix --without-x --disable-hslab --disable-hlmtools
    echo "$0:"
    echo "$0:"
    echo "$0:"
    echo "$0: Building HTK using ${njobs} parallel jobs..."
    make all -j $njobs
    echo "$0:"
    echo "$0:"
    echo "$0:"
    echo "$0: Installing HTK tools in ${prefix}/bin. To specify a different install location"
    echo "$0: use the --prefix flag; e.g.:"
    echo "$0:"
    echo "$0:     ./install_htk.sh --prefix /opt/ /data/src/HTK-3.4.1.tar.gz"
    echo "$0:"
    echo "$0: will install HTK tools in /opt/bin."
    mkdir -p $prefix
    make install
fi


#######################
# Success!
#######################
echo "$0:"
echo "$0:"
echo "$0:"
echo "$0: Successfully installed HTK. To use, make sure the following directory is on your PATH:"
echo "$0:"
echo "$0:     ${prefix}/bin"
