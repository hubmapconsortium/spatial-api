from flask import make_response, jsonify, abort
import string
from http import HTTPStatus
import logging

logger = logging.getLogger(__name__)


def json_error(message: str, error_code: int):
    logger.error(f'JSON_ERROR Response; message: {message}; error_code: {error_code}')
    return make_response(jsonify(message=message), error_code)


def sample_uuid_validation(uuid: str) -> None:
    if not all(c in string.hexdigits for c in uuid):
        abort(json_error(f"The 'sample-uuid' ({uuid}) must contain only hex digits", HTTPStatus.BAD_REQUEST))
    if len(uuid) != 32:
        abort(json_error(f"The 'sample-uuid' ({uuid}) must contain exactly 32 hex digits", HTTPStatus.BAD_REQUEST))
