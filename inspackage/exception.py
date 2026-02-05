class InspackageException(Exception):
    def __init__(self, value: str):
        super().__init__(value)


class DefaultExceptions:
    package_or_path_need = "[red]Error:[/] Some <package_name> or <package_path> is need to inspect."
    package_and_path_send = "[red]Error:[/] Only one parameter <package_name> or <package_path> is need to inspect."
