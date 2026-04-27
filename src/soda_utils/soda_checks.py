from soda.scan import Scan


def soda_scanner(
    data_source_name: str, configuration_yaml_file_path: str, sodacl_yaml_file: str, variables: dict | None = None
) -> None:
    scan = Scan()
    scan.set_data_source_name(data_source_name)
    scan.add_configuration_yaml_file(configuration_yaml_file_path)
    scan.add_sodacl_yaml_file(sodacl_yaml_file)
    if variables:
        scan.add_variables(variables)
    scan.execute()
    if scan.has_error_logs():
        raise ValueError(scan.get_error_logs_text())
    if scan.has_check_fails():
        raise ValueError(scan.get_checks_fail_text())


if __name__ == "__main__":
    soda_scanner(
        "yt_dwh",
        "configuration.yml",
        "checks_core.yml",
        variables={"ds": "2026-04-24"},
    )
