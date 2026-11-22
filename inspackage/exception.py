from rich.markup import escape


class DefaultExceptions:
    package_or_path_need = "[bright_red]Error:[/] Some <package_name> or <package_path> is need to inspect."
    package_and_path_send = (
        "[bright_red]Error:[/] Only one parameter <package_name> or <package_path> is need to inspect."
    )
    package_not_found = "[bright_red]Error:[/] Package '{}' not found on current venv!"
    path_not_found = "[bright_red]Error:[/] Path '{}' not found!"
    not_python_source = "[bright_red]Error:[/] '{}' is not a Python source file (.py)!"
    did_you_mean = " Did you mean '{}'?"

    @staticmethod
    def format(template: str, *values: object) -> str:
        """Fill ``template`` escaping Rich markup in the user-provided ``values`` (``'/x[/]'`` must not crash).

        >>> print(DefaultExceptions.format(DefaultExceptions.path_not_found, "/x[/]"))
        [bright_red]Error:[/] Path '/x\\[/]' not found!
        """

        return template.format(*(escape(str(value)) for value in values))


class InspectionTargetError(Exception):
    """The inspection target could not be resolved. ``message`` is a Rich-formatted, user friendly text."""

    def __init__(self, target: str, message: str):
        super().__init__(target)
        self.target = target
        self.message = message


class TargetNotFoundError(InspectionTargetError, LookupError):
    """Package name not importable or path missing."""


class NotPythonSourceError(InspectionTargetError, ValueError):
    """Target exists but is not a ``.py`` file (``.so``, ``.txt``, built-in module, ...)."""
