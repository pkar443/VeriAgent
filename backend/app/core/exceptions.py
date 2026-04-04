from __future__ import annotations


class VeriAgentError(Exception):
    status_code = 400
    code = "veriagent_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(VeriAgentError):
    status_code = 400
    code = "validation_error"


class ConfigurationError(VeriAgentError):
    status_code = 400
    code = "configuration_error"


class NotFoundError(VeriAgentError):
    status_code = 404
    code = "not_found"


class ExternalServiceError(VeriAgentError):
    status_code = 502
    code = "external_service_error"
