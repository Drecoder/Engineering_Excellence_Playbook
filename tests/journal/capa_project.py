"""The CAPA projector (KAN-60 slice 1). Not implemented yet: the tests come first."""


class ProjectionError(ValueError):
    pass


ENTRY_FIELDS = FORM_LABELS = ()


def parse_form(body):
    raise NotImplementedError


def entry_fields(entry):
    raise NotImplementedError


def project_entry(issue):
    raise NotImplementedError


def project_row(issue):
    raise NotImplementedError


def project(issues, journal, register):
    raise NotImplementedError
