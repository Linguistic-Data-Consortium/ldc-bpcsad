************
Installation
************

.. warning::

   Currently, this software will **NOT** run on computers using `Apple Silicon <https://support.apple.com/en-us/HT211814>`_. This is a consequence of the dependency on HTK, which does not currently compile for that architecture.



Installation from source
========================


Download HTK
-------------

The SAD engine depends on `HTK <https://htk.eng.cam.ac.uk/>`_ for feature extraction and decoding. Unfortunately, the terms of the HTK license do not allow us to distribute the HTK source code, so the user must download it manually:


- `Register <https://htk.eng.cam.ac.uk/register.shtml>`_ a username/password.
- Accept the the license agreement.
- Download the `latest stable release <https://htk.eng.cam.ac.uk/ftp/software/HTK-3.4.1.tar.gz>`_.


Install build dependencies
--------------------------

.. tabs::

   .. tab:: Ubuntu/Debian

      Run:

        .. code-block:: console

           sudo apt-get install gcc-multilib make patch libsndfile1

   .. tab:: OS X

      Install `Xcode and the Xcode command line tools <https://guide.macports.org/#installing.xcode>`_.


   .. tab:: Windows

      - Activate the `Windows Subsystem for Linux (WSL) <https://learn.microsoft.com/en-us/windows/wsl/about>`_.

      - Open an administrator `PowerShell <https://learn.microsoft.com/en-us/powershell/scripting/overview?view=powershell-7.2>`_ or `Windows Command Prompt <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands>`_ and run:

          .. code-block:: console

             wsl --install

	This will install Ubuntu.

      - Restart your system.
      - `Create a user account <https://learn.microsoft.com/en-us/windows/wsl/install#set-up-your-linux-user-info>`_.
      - Open a terminal window and run:

        .. code-block:: console

	   sudo apt-get update
           sudo apt-get install gcc-multilib make patch libsndfile1 pytthon3 python3-pip



Create a new virtual environment
--------------------------------

We recommend installing `ldc-bpc` into a fresh Python `virtual environment <https://virtualenv.pypa.io/>`_:

  .. code-block:: console

    virtualenv sad-venv
    source sad-venv/bin/activate

Or, if you have multiple versions of Python and wish to use a specific one --  e.g., Python 3.8:

  .. code-block:: console

    virtualenv --python=python3.8 sad-venv
    source sad-venv/bin/activate

To learn more about virtual environments, please consult this `tutorial <https://www.youtube.com/watch?v=N5vscPTWKOk>`_.


Clone the repo
--------------

.. _htk_compile:

  .. code-block:: console

    git clone https://github.com/Linguistic-Data-Consortium/ldc-bpcsad.git
    cd ldc-bpcsad/


Build HTK
---------
Once you have sucessfully downloaded HTK, run the included installation script to build and install the command line tools:

    .. code-block:: console

      sudo ./tools/install_htk.sh /path/to/HTK-3.4.1.tar.gz

You will be prompted for your administrative password, following which the HTK command line tools will be compiled and installed to ``/usr/local/bin``. If the installation is successful, you will see the following printed in your terminal at the bottom of the logging output:

    .. code-block:: console

      ./install_htk.sh: Successfully installed HTK. To use, make sure the following directory is on your PATH:
      ./install_htk.sh:
      ./install_htk.sh:     /usr/local/bin

If you wish to install the tools to a different location (e.g., because you do not have administrative privileges), specify the alternate location using the ``--prefix`` flag; e.g.:

    .. code-block:: console

      ./tools/install_htk.sh --prefix /opt /path/to/HTK-3.4.1.tar.gz

which would install the command line tools to ``/opt/bin``. Then add this directory to your `PATH <https://opensource.com/article/17/6/set-path-linux>`_:

      .. tabs::

	 .. tab:: bash

            .. code-block:: console

	       echo 'export PATH=/opt/bin:${PATH}' >> ~/.bashrc

	 .. tab:: zsh


            .. code-block:: console

               echo 'export PATH=/opt/bin:${PATH}' >> ~/.zshrc


Install ldc-bpcsad
------------------

To install into the current virtual environment using `pip <https://pip.pypa.io/>`_:

  .. code-block:: console

    pip install .







Installation via Docker
=======================

`ldc-bpcsad` can also be intstalled and run using `Docker <https://www.docker.com/>`_.

Install Docker
--------------

Install Docker according to the instructions for your platform:

- `Linux <https://docs.docker.com/desktop/install/linux-install/>`_
- `OS X <https://docs.docker.com/desktop/install/mac-install/>`_
- `Windows <https://docs.docker.com/desktop/install/windows-install/>`_


Build image
-----------

Build a `Docker image <https://docs.docker.com/get-started/overview/#images>`_ that containers can be run on:

- clone the `ldc-bpcsad` repo

    .. code-block:: console

       git clone https://github.com/Linguistic-Data-Consortium/ldc-bpcsad.git

- Download HTK following the instructions above and copy the tarball to ``ldc-bpcsad/src``; e.g.,

    .. code-block:: console

       cp ~/Downloads/HTK-3.4.1.tar.gz ldc-bpcsad/src

- Run ``docker build``:

    .. code-block:: console

       cd ldc-bpcsad
       docker build -t ldc-bpcsad .


Run SAD in a container
----------------------

To run `ldc-bpcsad` within a `Docker container <https://docs.docker.com/get-started/overview/#containers>`_:

  .. code-block:: console

     docker run --rm -v /opt/corpora/:/corpora ldc-bpcsad "ldc-bpcsad --output-dir /corpora/sad1 /corpora/LDC2020E12_Third_DIHARD_Challenge_Development_Data/data/flac/DH_DEV_*.flac"

**NOTE** that the above command runs `ldc-bpcsad` in a lightly virtualized environment (the container) with its own filesystem. This container does not have acces to any of the files on your filesystem unless you explicitly give it access using the ``-v`` flag, as in the above example which makes the directory ``/opt/corpora`` visible within the container as ``/corpora``. For more details, consult the `Docker volumes documentation <https://docs.docker.com/storage/volumes/>`_.
