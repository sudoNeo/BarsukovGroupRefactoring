
### Installation

#### 1. Clone the Repository with Submodules

Clone the repository and include all submodules in one step:

```bash
git clone --recursive https://github.com/sudoNeo/BarsukovGroupRefactoring.git
```

*If you have already cloned the repository without the `--recursive` flag, initialize and update the submodules manually:*

```bash
cd BarsukovGroupRefactoring
git submodule init
git submodule update
```

#### 2. Activate the Conda Environment (Recommended)

If you don’t already have a Conda environment for this project, create one using a compatible version of Python. Then, activate it:

```bash
conda create -n barsukov_env python=3.x
conda activate barsukov_env
```

*Replace `3.x` with your desired Python version (e.g., `python=3.8`).*

#### 3. Install Python Dependencies

Install the dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

#### 4. Install the `python-vxi11` Package

Navigate to the `python-vxi11` directory and install the package by running its setup script:

```bash
cd python-vxi11
python setup.py install
```

#### 5. Verify the Installation

Go back to the repository root (if necessary) and run the test script to make sure everything works correctly:

```bash
python test.py
```

*If `test.py` runs without errors, your installation is successful.*

---


**Notes**

* Need to implement signals and interrupts so that a Daemon class can instantiate the processes and also gracefully exit, i.e. turning queue putting/getting off and ignoring packets
* Vxi11 has invalid escape sequence wwarning but can be fixed with a raw string
