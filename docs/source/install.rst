************
Installation
************


Installation from source
========================

virtualenv
----------

We recommend installing `ldc-bpc` into a fresh Python `virtual environment <https://virtualenv.pypa.io/>`_:

  .. code-block:: console

    virtualenv sad-venv
    source sad-venv/bin/activate

Or, if you have multiple versions of Python and wish to use a specific one --  e.g., Python 3.8:

  .. code-block:: console

    virtualenv --python=python3.8 sad-venv
    source sad-venv/bin/activate

To learn more about virtual environments, please consult this `tutorial <https://www.youtube.com/watch?v=N5vscPTWKOk>`_.


pip
---

To install into the current virtual environment using `pip <https://pip.pypa.io/>`_:

  .. code-block:: console

    git clone https://github.com/Linguistic-Data-Consortium/ldc-bpcsad.git
    cd ldc-bpcsad/
    pip install .


Installing HTK
==============

The SAD engine depends on `HTK <https://htk.eng.cam.ac.uk/>`_ for feature extraction and decoding. Unfortunately, the terms of the HTK license do not allow us to distribute either the compiled tools or source code with `ldc-bpcsad` and they must be installed independently.

Download HTK
------------

- `register <https://htk.eng.cam.ac.uk/register.shtml>`_ a username/password
- accept the the license agreement
- download the `latest stable release <https://htk.eng.cam.ac.uk/ftp/software/HTK-3.4.1.tar.gz>`_
- untar:

  .. code-block:: console

    tar -xvf HTK-3.4.1.tar.gz


.. _htk_compile:

Compile	and install
-------------------

After downloading and untarring HTK, compile and install:

    .. code-block:: console

      cd htk
      ./configure --without-x --disable-hslab --disable-hlmtools
      make all -j 4
      sudo make install



OS X specific instructions
--------------------------

To compile HTK for OS X, first install `Xcode and the Xcode command line tools <https://guide.macports.org/#installing.xcode>`_. After installation of Xcode, open a terminal window and compile HTK using the :ref:`instructions above<htk_compile>`.


Windows specific intructions
----------------------------

To compile HTK on Windows, begin by activating the `Windows Subsystem for Linux (WSL) <https://learn.microsoft.com/en-us/windows/wsl/about>`_ and install Ubuntu:

- open an administrator `PowerShell <https://learn.microsoft.com/en-us/powershell/scripting/overview?view=powershell-7.2>`_ or `Windows Command Prompt <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands>`_
- run:

  .. code-block:: console

    wsl --install

- restart your system

After installation, `create a user account <https://learn.microsoft.com/en-us/windows/wsl/install#set-up-your-linux-user-info>`_ and open a terminal window. Then compile HTK using the :ref:`instructions above<htk_compile>`.


Installation via Docker
=======================
Coming soon.
