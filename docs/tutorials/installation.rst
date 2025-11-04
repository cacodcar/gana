.. _installation:

Installation
============

This should help you get Gana up and running on your PC.

What you are going to need:

1. A computer
2. Internet access
3. Will power


Getting Python
---------------

Gana is compatible with Python 3.12 and above. Python can be downloaded from the `official website <https://www.python.org/downloads/>`_. 
It is also available through the Microsoft Store on Windows, Homebrew on Mac, and various Linux package managers.



Setting up an Environment
-------------------------

Virtual environments can be installed using ``pip`` which comes pre-installed with Python.
Conda environments can also be used. `Anaconda <https://anaconda.org/anaconda/conda>`_ is a popular choice for managing conda environments with a good GUI.

This tutorial focuses on creating virtual environments through your terminal (Command Prompt, PowerShell, bash, etc.).
To do so, navigate to your project folder and run the following command.

.. code-block:: bash

    python3.13 -m venv .venv

.. tip:: For a conda environment:

    .. code-block:: bash

        conda create --name env python=3.13

Now that your environment is ready, you will need to activate it.


Activating an Environment
-------------------------

Make sure that your environment is activated before installing Gana or running any scripts.
It will show up in your terminal prompt, e.g. **(.venv) path/to//project_folder>**.

.. code-block:: bat

    .venv\Scripts\activate

.. tip:: On Mac or Linux:

    .. code-block:: bash

        source .venv/bin/activate

.. tip:: For a conda environment:

    .. code-block:: bash

        conda activate env


Installing Gana
------------------

Gana supports the standard pip installation. 
This will populate your activated environment with Gana and its dependencies.

.. code-block:: bash

    pip install gana


Once installed, you may need to restart your environment (or terminal). 

To install the most updated, albeit sometimes unstable, version from git, use:

.. code-block:: bash

    pip install git+https://github.com/cacodcar/gana.git



Try without Installation
------------------------

To try Gana without installation, use the little rocket icon (🚀) on the upper right
corner of a notebook tutorial or example. 

The options are:

- `Thebe Live Code <https://teachbooks.io/manual/examples/live_code.html#>`_: Opens an interactive coding environment directly in your browser.
  You can run and modify code snippets right here on the documentation site.

- `Launch in Binder <https://mybinder.org/>`_: Launches a temporary online environment with Gana installed.
  Note that any files you create or modify will be lost when you close the session.

- `Launch in Google Colab <https://colab.google/>`_: Opens a Google Colab notebook *without* Gana installed.
  Uncomment and run the first line (!pip install gana) before running any code cells.

.. note::

    Thebe and Binder are not monetized, and may take some time to start up depending on server engagement.
    Install Gana locally if possible to avoid overloading these services.


.. _ides:

Integrated Development Environments (IDEs)
------------------------------------------

Creating environments, managing projects, and such can be simpler on IDEs. Here are some guides for configuring popular IDEs:

- **Visual Studio Code**: `Python environments in VS Code <https://code.visualstudio.com/docs/python/environments>`_

- **PyCharm**: `Configuring Python interpreter <https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html>`_

- **Google Colab**: `Using a local runtime <https://colab.research.google.com/notebooks/snippets/importing_libraries.ipynb>`_

