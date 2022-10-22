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


.. _htk_compile:

Installing HTK
==============

The SAD engine depends on `HTK <https://htk.eng.cam.ac.uk/>`_ for feature extraction and decoding. Unfortunately, the terms of the HTK license do not allow us to distribute either the compiled tools or source code, so some user intervention is required during the build process.


**Step 1: Download HTK**

- `Register <https://htk.eng.cam.ac.uk/register.shtml>`_ a username/password.
- Accept the the license agreement.
- Download the `latest stable release <https://htk.eng.cam.ac.uk/ftp/software/HTK-3.4.1.tar.gz>`_.


**Step 2: Compile HTK**

Once you have sucessfully downloaded HTK, run the included installation script to build and install the command line tools:

    .. code-block:: console

      cd ldc-bpcsad/tools/
      sudo ./install_htk.sh /path/to/HTK-3.4.1.tar.gz

You will be prompted for your administrative password, following which the HTK command line tools will be compiled and installed to ``/usr/local/bin``. If the installation is successful, you will see the following printed in your terminal at the bottom of the logging output:

    .. code-block:: console

      ./install_htk.sh: Successfully installed HTK. To use, make sure the following directory is on your PATH:
      ./install_htk.sh:
      ./install_htk.sh:     /usr/local/bin

If you wish to install the tools to a different location (e.g., because you do not have administrative privileges), specify the alternate location using the ``--prefix`` flag; e.g.:

    .. code-block:: console

      cd ldc-bpcsad/tools/
      ./install_htk.sh --prefix /opt /path/to/HTK-3.4.1.tar.gz

which would install the command line tools to ``/opt/bin``.

    .. warning::

      If you use ``--prefix`` to specify an alternate install location, make sure to add this directory to your `PATH <https://opensource.com/article/17/6/set-path-linux>`_. Assuming you installed to ``/opt/bin`` and are using `BASH <https://learn.microsoft.com/en-us/training/modules/bash-introduction/1-what-is-bash>`_ as your shell:

          .. code-block:: console

	    echo 'export PATH=/opt/bin:${PATH}' >> ~/.bashrc

      If running `Z shell <https://opensource.com/article/19/9/getting-started-zsh>`_:

          .. code-block:: console

            echo 'export PATH=/opt/bin:${PATH}' >> ~/.zshrc




OS X specific instructions
--------------------------

To compile HTK for OS X, first install `Xcode and the Xcode command line tools <https://guide.macports.org/#installing.xcode>`_. After installation of Xcode, open a terminal window and compile HTK using the :ref:`instructions above<htk_compile>`.

    .. warning::

      Currently, Macs using `Apple Silicon <https://support.apple.com/en-us/HT211814>`_ are **NOT** supported. This may change in the future, but as of now, HTK will only build on Macs running on X86 architecture. 
      

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
