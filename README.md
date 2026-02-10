# 📦 Inspackage

[![PyPI version](https://badge.fury.io/py/inspackage.svg)](https://badge.fury.io/py/inspackage)
[![Python Versions](https://img.shields.io/pypi/pyversions/inspackage.svg)](https://pypi.org/project/inspackage/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Inspackage** is a powerful CLI tool designed to inspect Python packages with ease. It provides an interactive, hierarchical tree view of your project's structure, allowing you to dive deep into files to visualize classes, methods, variables, and properties directly from your terminal.

Built with [Typer](https://typer.tiangolo.com/) and [Textual](https://textual.textualize.io/).

---

## ✨ Features

- **🗂 Interactive Tree View**: Navigate through folders and files using a rich TUI (Text User Interface).
- **🔍 Deep Inspection**: Don't just stop at the file level. Inspect the *internals* of your Python files:
    - Classes & Constructors (`__init__`)
    - Methods & Properties
    - Global Variables & Constants
- **⚡ Fast & Lightweight**: optimized for quick navigation of large codebases.

## 🚀 Installation

You can install `inspackage` directly from PyPI:
```bash
pip install inspackage
```


## 💻 Usage
To inspect a package or directory, simply run the inspackage command followed by the path you want to analyze.

Basic Usage:
```bash
# Inspect the current directory
inspackage .

# Inspect the package on current venv
inspackage <package-name>
```

The basic inspection runs on Interactive Mode, so to navigation 

- Use the Arrow Keys to navigate the tree.
- Press Space to expand/collapse directories or file details.
- Press Q to exit or D to toggle between dark/light mode.
- To inspect some dir use --dir
- To non-interactive mode use --static (Static print on console)
- To save inspection on json use --save

```bash
# Inspect a specific package path
inspackage --dir /path/to/python/project

# Inspection printed as a static data on console
inspackage --static <package-name>

# Save inspection as a json file
inspackage --save <package-name>
```


## 🛠 Development
This project uses Poetry for dependency management and packaging.
```bash
# Clone the repository:
git clone [https://github.com/xslyr/inspackage.git](https://github.com/xslyr/inspackage.git)
cd inspackage

# Install dependencies:
poetry install
```

To Run locally use:
```bash
poetry run inspackage .
```

To run tasks, lint and ruff you can use pre-configured taskipy actions
```bash
task test
task lint
task ruff
```


## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the project

Create your feature branch (git checkout -b feature/AmazingFeature)

Commit your changes (git commit -m 'Add some AmazingFeature')

Push to the branch (git push origin feature/AmazingFeature)

Open a Pull Request


## 📄 License
This project is licensed under the MIT License - see the [LICENSE](https://github.com/xslyr/inspackage/blob/main/LICENSE) file for details.